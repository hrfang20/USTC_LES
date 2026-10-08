"""Download actual OSM buildings and the four boundary roads for delineation."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
QUERY = '''[out:json][timeout:90];
(
 way["building"](31.82,117.245,31.855,117.29);
 relation["building"](31.82,117.245,31.855,117.29);
 way["highway"]["name"~"黄山路|太湖路|太湖东路|太湖西路|金寨路|宿松路"](31.82,117.245,31.855,117.29);
);out body;>;out skel qt;'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', default='https://overpass-api.de/api/interpreter')
    parser.add_argument('--osm-api', action='store_true', help='Use OSM map API instead of Overpass')
    args = parser.parse_args()
    output = ROOT / 'data/raw/osm_area.json'
    headers = {'User-Agent': 'USTC-LES-research-preprocessing/0.1'}
    if args.osm_api:
        response = requests.get('https://api.openstreetmap.org/api/0.6/map',
                                params={'bbox': '117.255,31.826,117.277,31.846'},
                                headers=headers, timeout=120)
    else:
        response = requests.post(args.endpoint, data={'data': QUERY}, timeout=120,
                                 headers=headers)
    response.raise_for_status()
    if args.osm_api:
        elements = []
        document = ET.fromstring(response.content)
        for element in document:
            if element.tag not in ('node', 'way', 'relation'):
                continue
            item = {'type': element.tag, 'id': int(element.attrib['id']),
                    'tags': {t.attrib['k']: t.attrib['v'] for t in element.findall('tag')}}
            if element.tag == 'node':
                item.update(lon=float(element.attrib['lon']), lat=float(element.attrib['lat']))
            elif element.tag == 'way':
                item['nodes'] = [int(n.attrib['ref']) for n in element.findall('nd')]
            else:
                item['members'] = [dict(type=m.attrib['type'], ref=int(m.attrib['ref']),
                                       role=m.attrib['role']) for m in element.findall('member')]
            elements.append(item)
        data = {'source': response.url, 'elements': elements,
                'note': 'OSM map API search bbox, not the final study boundary'}
    else:
        data = response.json()
    if data.get('remark'):
        raise RuntimeError(data['remark'])
    if not data.get('elements'):
        raise RuntimeError('No OSM elements returned')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    (output.parent / 'osm_query.txt').write_text(QUERY, encoding='utf-8')
    print(f'Saved {len(data["elements"])} OSM elements to {output}')
    print('License: OpenStreetMap contributors, ODbL. Search bbox is not the final study boundary.')


if __name__ == '__main__':
    main()
