"""Read downloaded OSM data, delineate the road block, and export uDALES STL.

Run using turbpy. Dependencies are kept in vendor/python-deps, not another env.
No flow simulation is started. Heights without OSM measurements are scenarios.
"""
import argparse
import csv
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'vendor/python-deps'), str(ROOT / 'vendor/u-dales/tools/python')]

import numpy as np
import trimesh
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, mapping
from shapely.ops import polygonize, transform, unary_union
from udgeom import UDGeom, add_ground

ROADS = ['黄山路', '太湖路', '金寨路', '宿松路']


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                              default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x)) + '\n', encoding='utf-8')


def parts(geometry):
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return []


def number(value):
    if value is None:
        return None
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(m|ft)?\s*', str(value))
    if not match:
        return None
    result = float(match[1]) * (0.3048 if match[2] == 'ft' else 1)
    return result if result > 0 else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--default-height', type=float, default=12.)
    parser.add_argument('--floor-height', type=float, default=3.3)
    parser.add_argument('--min-area', type=float, default=25.)
    parser.add_argument('--simplify', type=float, default=0.5)
    parser.add_argument('--buffer', type=float, default=150.)
    parser.add_argument('--ground-facet-size', type=float, default=20.)
    args = parser.parse_args()
    for key in ('default_height', 'floor_height', 'min_area', 'buffer', 'ground_facet_size'):
        if not math.isfinite(getattr(args, key)) or getattr(args, key) <= 0:
            parser.error(f'{key} must be positive and finite')
    if not math.isfinite(args.simplify) or args.simplify < 0:
        parser.error('simplify must be nonnegative and finite')
    data_path = ROOT / 'data/raw/osm_area.json'
    data = json.loads(data_path.read_text(encoding='utf-8'))
    elements = data['elements']
    nodes = {n['id']: (n['lon'], n['lat']) for n in elements if n['type'] == 'node'}
    ways = {w['id']: w for w in elements if w['type'] == 'way'}
    forward = Transformer.from_crs('EPSG:4326', 'EPSG:32650', always_xy=True)
    inverse = Transformer.from_crs('EPSG:32650', 'EPSG:4326', always_xy=True)

    def line(way):
        return transform(forward.transform, LineString([nodes[n] for n in way['nodes']]))

    road_lines = {name: [line(w) for w in ways.values()
                        if w.get('tags', {}).get('name') == name and w['tags'].get('highway')]
                  for name in ROADS}
    if any(not lines for lines in road_lines.values()):
        raise RuntimeError('Boundary road missing from downloaded data')
    faces = list(polygonize(unary_union([ln for lines in road_lines.values() for ln in lines])))
    seed = transform(forward.transform, Point(117.263, 31.838))
    candidates = [p for p in faces if p.contains(seed)]
    if not candidates:
        raise RuntimeError('The four roads do not enclose the campus locator; refusing a bbox fallback')
    boundary = max(candidates, key=lambda p: p.area)
    contributions = {name: boundary.boundary.intersection(unary_union(lines).buffer(0.05)).length
                     for name, lines in road_lines.items()}
    if any(length < 10 for length in contributions.values()):
        raise RuntimeError(f'Enclosing polygon does not touch all four roads: {contributions}')
    minx, miny, maxx, maxy = boundary.bounds
    origin = (minx - args.buffer, miny - args.buffer)
    domain = [math.ceil((maxx - origin[0] + args.buffer) / 5) * 5,
              math.ceil((maxy - origin[1] + args.buffer) / 5) * 5, 400]
    local = lambda x, y, z=None: (np.asarray(x) - origin[0], np.asarray(y) - origin[1])
    save_json(ROOT / 'data/geometry/study_area.geojson', {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': mapping(transform(inverse.transform, boundary)),
         'properties': {'source': 'OpenStreetMap mapped road carriageways', 'boundary_roads': ROADS,
                        'google_maps_verified': False, 'boundary_convention': 'interior enclosed face of mapped carriageways'}}]})

    records, skipped, relation_members = [], [], set()
    for relation in elements:
        if relation['type'] != 'relation' or relation.get('tags', {}).get('building') in (None, 'no'):
            continue
        try:
            outer_lines = [line(ways[m['ref']]) for m in relation['members']
                           if m['type'] == 'way' and m['role'] in ('outer', '')]
            inner_lines = [line(ways[m['ref']]) for m in relation['members']
                           if m['type'] == 'way' and m['role'] == 'inner']
            outer = unary_union(list(polygonize(unary_union(outer_lines))))
            inner = unary_union(list(polygonize(unary_union(inner_lines))))
            geometry = outer.difference(inner)
            if geometry.is_empty or not geometry.is_valid:
                raise ValueError('Invalid relation footprint')
            records.append((f'relation/{relation["id"]}', relation['tags'], geometry))
            relation_members.update(m['ref'] for m in relation['members'] if m['type'] == 'way')
        except (KeyError, ValueError) as exc:
            skipped.append({'id': f'relation/{relation["id"]}', 'reason': str(exc)})
    for w in ways.values():
        tags = w.get('tags', {})
        if tags.get('building') in (None, 'no') or w['id'] in relation_members:
            continue
        identity = f'way/{w["id"]}'
        if w['nodes'][0] != w['nodes'][-1]:
            skipped.append({'id': identity, 'reason': 'Unclosed footprint'})
            continue
        polygon = Polygon(line(w).coords)
        if not polygon.is_valid:
            skipped.append({'id': identity, 'reason': 'Invalid footprint; not silently repaired'})
            continue
        records.append((identity, tags, polygon))

    features, meshes, inventory, projected, height_counts = [], [], [], [], Counter()
    for identity, tags, footprint in records:
        if not footprint.intersects(boundary):
            continue
        height = number(tags.get('height'))
        if height is not None:
            source, uncertainty = 'OSM height tag (not independently verified)', None
        else:
            levels = number(tags.get('building:levels'))
            if levels is not None:
                height, source, uncertainty = levels * args.floor_height, 'OSM levels times assumed floor height', levels * 0.5
            else:
                height, source, uncertainty = args.default_height, 'assumed default scenario, no measured height', args.default_height * 0.5
        if footprint.area < args.min_area and not tags.get('name') and height < 20:
            skipped.append({'id': identity, 'reason': 'Small unnamed low structure below area threshold'})
            continue
        if tags.get('min_height') or tags.get('building:min_level') or tags.get('building') == 'roof':
            skipped.append({'id': identity, 'reason': 'Elevated/roof-only structure needs separate treatment'})
            continue
        simplified = footprint.simplify(args.simplify, preserve_topology=True)
        if abs(simplified.area - footprint.area) / footprint.area > 0.02 or len(parts(simplified)) != len(parts(footprint)):
            simplified = footprint
        props = {'building_id': identity, 'name': tags.get('name', ''), 'height_m': height,
                 'height_source': source, 'height_uncertainty_m': uncertainty,
                 'footprint_source': f'https://www.openstreetmap.org/{identity}',
                 'coordinate_system_verified': False, 'source_date': None,
                 'osm_tags': tags, 'simplification_note': f'Topology-preserving {args.simplify} m tolerance; area change <= 2%; flat roof extrusion',
                 'footprint_area_m2': footprint.area, 'outside_fraction': footprint.difference(boundary).area / footprint.area}
        features.append({'type': 'Feature', 'geometry': mapping(transform(inverse.transform, footprint)), 'properties': props})
        geometry_local = transform(local, simplified)
        projected.append({'type': 'Feature', 'geometry': mapping(geometry_local), 'properties': props})
        for part in parts(geometry_local):
            mesh = trimesh.creation.extrude_polygon(part, height, engine='earcut')
            if not mesh.is_watertight or mesh.volume <= 0:
                raise RuntimeError(f'Invalid extrusion: {identity}')
            meshes.append(mesh)
        inventory.append({k: props[k] for k in ('building_id', 'name', 'height_m', 'height_source', 'height_uncertainty_m', 'footprint_area_m2')})
        height_counts[source] += 1
    if not meshes:
        raise RuntimeError('No building geometry inside road boundary')

    # Actual solid union removes overlapping/interior faces while retaining height steps.
    solid = trimesh.boolean.union(meshes, engine='manifold')
    if not solid.is_watertight or not solid.is_winding_consistent or solid.volume <= 0:
        raise RuntimeError('Union of building solids is invalid')
    case = ROOT / 'cases/001'
    case.mkdir(parents=True, exist_ok=True)
    solid.export(case / 'buildings.stl')
    geom = UDGeom(case)
    geom.load('buildings.stl')
    qa = geom.check(require_single_component=False)
    if not qa['valid']:
        raise RuntimeError(f'Official geometry check failed: {qa["issues"]}')
    if not geom.stl.is_watertight or not geom.stl.is_winding_consistent:
        raise RuntimeError('STL round trip failed mesh validation')
    # The uDALES surface is roofs/walls plus exposed ground, without buried bases.
    surface = geom.stl.copy()
    buried = np.all(np.isclose(surface.triangles[:, :, 2], 0., atol=1e-7), axis=1)
    surface.update_faces(~buried)
    surface.remove_unreferenced_vertices()
    grounded = add_ground(surface, domain[0], domain[1], edgelength=args.ground_facet_size)
    grounded.path = case
    grounded.save('geom.001.stl')
    ground_qa = grounded.check(require_single_component=False)
    if not ground_qa['valid']:
        raise RuntimeError(f'Grounded geometry check failed: {ground_qa["issues"]}')
    save_json(case / 'geometry_qa_details.json', {'buildings': qa, 'with_ground': ground_qa})
    save_json(ROOT / 'data/geometry/buildings.geojson', {'type': 'FeatureCollection', 'features': features})
    save_json(ROOT / 'data/geometry/buildings_local.json', {'type': 'FeatureCollection',
        'coordinate_reference': 'Local metres, east/north/up, origin offset from EPSG:32650; not RFC7946 GeoJSON',
        'origin_utm50n_m': origin, 'features': projected})
    with (ROOT / 'data/geometry/building_inventory.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(inventory[0]))
        writer.writeheader()
        writer.writerows(inventory)
    save_json(ROOT / 'data/geometry/skipped_features.json', skipped)
    revision = subprocess.check_output(['git', '-C', str(ROOT / 'vendor/u-dales'), 'rev-parse', 'HEAD'], text=True).strip()
    report = {'solver': 'uDALES', 'udales_revision': revision, 'source': 'OpenStreetMap contributors, ODbL',
        'source_endpoint': data.get('source', 'Overpass'), 'google_maps_verified': False,
        'study_area_m2': boundary.area, 'boundary_road_contact_m': contributions,
        'origin_utm50n_m': origin, 'origin_wgs84': inverse.transform(*origin),
        'suggested_domain_m': domain, 'horizontal_buffer_m': args.buffer,
        'buffer_note': 'Planning buffer only; no surrounding buffer buildings acquired for the exported STL',
        'building_records': len(features), 'height_sources': dict(height_counts),
        'default_height_m': args.default_height, 'floor_height_m': args.floor_height,
        'stl_file': 'cases/001/buildings.stl', 'stl_triangles': len(geom.stl.faces),
        'stl_bounds_m': geom.stl.bounds, 'stl_watertight': bool(geom.stl.is_watertight),
        'stl_winding_consistent': bool(geom.stl.is_winding_consistent),
        'udales_geometry_check': {'valid': qa['valid'], 'issues': qa['issues'], 'summary': qa['summary']},
        'ground_stl_file': 'cases/001/geom.001.stl', 'ground_stl_triangles': len(grounded.stl.faces),
        'ground_geometry_check': {'valid': ground_qa['valid'], 'issues': ground_qa['issues'], 'summary': ground_qa['summary']},
        'status': 'geometry_read_by_official_UDGeom_not_full_IBM_preprocessing_or_simulation',
        'remaining': ['Google Maps layout and data completeness verification', 'Building height calibration',
                      'IBM grid preprocessing', 'Stable ABL forcing/walls and namoptions',
                      'Compute-platform assessment at simulation launch stage']}
    save_json(case / 'geometry_report.json', report)
    config_path = ROOT / 'configs/campus_draft.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['solver'] = 'uDALES'
    config['coordinate_origin_wgs84'] = list(inverse.transform(*origin))
    config['domain_m'] = domain
    config['study_area']['boundary_geometry_file'] = 'data/geometry/study_area.geojson'
    config['study_area']['boundary_status'] = 'delineated_from_OSM_pending_Google_Maps_verification'
    config['study_area']['boundary_convention'] = 'interior enclosed face of mapped carriageways'
    config['udales_geometry_file'] = 'cases/001/geom.001.stl'
    config['geometry_simplification']['footprint_tolerance_m'] = args.simplify
    config['geometry_simplification']['minimum_unnamed_low_structure_area_m2'] = args.min_area
    config['study_area'].pop('include_all_buildings_within_extent', None)
    config['study_area']['include_non_campus_buildings'] = True
    save_json(config_path, config)
    print(f'Exported {len(features)} building records, {len(geom.stl.faces)} STL triangles')
    print('Official uDALES UDGeom successfully read the STL. No LES was run.')
    print('Height sources:', dict(height_counts))
    print('Suggested domain (m):', domain)

    # Scientific QA artifact, explicitly labelled as scenario geometry.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import Polygon as PlotPolygon
    patches, values = [], []
    fig, ax = plt.subplots(figsize=(9, 11))
    for feature in projected:
        from shapely.geometry import shape
        for polygon in parts(shape(feature['geometry'])):
            patches.append(PlotPolygon(np.asarray(polygon.exterior.coords), closed=True))
            values.append(feature['properties']['height_m'])
            for hole in polygon.interiors:
                ax.fill(*np.asarray(hole.coords).T, color='white', zorder=3)
    collection = PatchCollection(patches, cmap='viridis', edgecolor='black', linewidth=0.4)
    collection.set_array(np.array(values))
    ax.add_collection(collection)
    outline = transform(local, boundary)
    ax.plot(*np.array(outline.exterior.coords).T, 'r--', linewidth=1.5, label='OSM road-bounded study area')
    ax.set(xlim=(0, domain[0]), ylim=(0, domain[1]), xlabel='Local east (m)', ylabel='Local north (m)',
           title=f'USTC road block: {len(features)} OSM building records\nHeights include assumptions; Google Maps verification pending')
    ax.set_aspect('equal')
    ax.legend(loc='upper right')
    fig.colorbar(collection, ax=ax, label='Scenario building height (m)', shrink=0.7)
    fig.tight_layout()
    fig.savefig(case / 'geometry_overview.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
