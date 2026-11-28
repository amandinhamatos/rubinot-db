# Coleta a lista de bosses do Bosstiary (TibiaWiki), com sprite, categoria e level/acesso (estimados).
# Uso: python coletar_bosses.py   (na mesma pasta do index.html)
import json, re, os, time, subprocess, urllib.request, urllib.parse, html.parser
from concurrent.futures import ThreadPoolExecutor
API = 'https://tibia.fandom.com/api.php'
BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(AQUI, 'img', 'bosses'); os.makedirs(IMG, exist_ok=True)
os.makedirs(os.path.join(AQUI, 'data'), exist_ok=True)

def api(**p):
    url = API + '?' + urllib.parse.urlencode(p) + '&format=json'
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': BROWSER}), timeout=40) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception: time.sleep(2)
    return {}

class T(html.parser.HTMLParser):
    def __init__(s): super().__init__(); s.tabs = []; s.r = None; s.c = None; s.hd = ''; s.inh = False
    def handle_starttag(s, tag, a):
        a = dict(a)
        if tag in ('h2', 'h3', 'h4'): s.inh = True; s.hd = ''
        elif tag == 'table': s.tabs.append({'h': s.hd, 'rows': []})
        elif tag == 'tr' and s.tabs: s.r = {'cells': [], 'imgs': []}; s.tabs[-1]['rows'].append(s.r)
        elif tag in ('td', 'th') and s.r is not None: s.c = []
        elif tag == 'img' and s.r is not None:
            u = a.get('data-src') or a.get('src') or ''
            if u.startswith('http'): s.r['imgs'].append(u)
    def handle_endtag(s, tag):
        if tag in ('h2', 'h3', 'h4'): s.inh = False
        elif tag in ('td', 'th') and s.c is not None and s.r is not None:
            s.r['cells'].append(' '.join(''.join(s.c).split())); s.c = None
    def handle_data(s, d):
        if s.inh: s.hd += d
        if s.c is not None: s.c.append(d)

h = api(action='parse', page='Bosstiary/Categories', prop='text', redirects=1).get('parse', {}).get('text', {}).get('*', '')
p = T(); p.feed(h)
print(f'Tabelas na página: {len(p.tabs)}')
bosses = {}; cat = 'Nemesis'
dbg = open(os.path.join(AQUI, 'data', 'debug_bosses.txt'), 'w', encoding='utf-8')
for k, t in enumerate(p.tabs):
    m = re.search(r'(Bane|Archfoe|Nemesis)', t['h'])
    if m: cat = m.group(1)
    dbg.write(f'## tabela {k} cab="{t["h"][:40]}" cat={cat} linhas={len(t["rows"])}\n')
    for r in t['rows'][:25]: dbg.write(' | '.join(x[:40] for x in r['cells']) + f'  [imgs={len(r["imgs"])}]\n')
    for r in t['rows']:
        nome = next((c for c in r['cells'] if re.search(r'[A-Za-z]{3}', c) and len(c) < 60 and not re.match(r'^(Creature|Boss|HP|Exp|Charms|Difficulty|Loot)$', c, re.I)), '')
        if not nome or not r['imgs'] or nome in bosses: continue
        bosses[nome] = {'n': nome, 'c': cat, 'u': r['imgs'][0], 'f': '', 'lv': None, 'q': ''}
print(f'Bosses encontrados: {len(bosses)}', {c: sum(1 for b in bosses.values() if b['c'] == c) for c in ('Bane', 'Archfoe', 'Nemesis')})
nomes = sorted(bosses)
LV = [r'(?:minimum|min\.?|required|requires?)\s+level\s+(?:of\s+)?(\d{2,4})', r'level\s+(\d{2,4})\s*(?:\+|or higher|or above|and above|required)', r'(?:at least|from)\s+level\s+(\d{2,4})']
for i in range(0, len(nomes), 40):
    j = api(action='query', prop='revisions', rvprop='content', rvslots='main', titles='|'.join(nomes[i:i+40]))
    for pg in j.get('query', {}).get('pages', {}).values():
        t = pg.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')[:7000]
        b = bosses.get(pg.get('title'))
        if not b: continue
        for rx in LV:
            m = re.search(rx, t, re.I)
            if m: b['lv'] = int(m.group(1)); break
        q = re.search(r'\[\[([^\]\|]*Quest[^\]\|]*)(?:\|[^\]]*)?\]\]', t)
        if q: b['q'] = q.group(1)
print(f'Com level estimado: {sum(1 for b in bosses.values() if b["lv"])} de {len(bosses)} | com quest: {sum(1 for b in bosses.values() if b["q"])}')
def tipo(d):
    if d[:4] == b'GIF8': return 'gif'
    if d[:4] == b'\x89PNG': return 'png'
    if d[:4] == b'RIFF' and d[8:12] == b'WEBP': return 'webp'
    return None
def baixar(b):
    base = re.sub(r'[^A-Za-z0-9]+', '_', b['n']).lower().strip('_')
    for e in ('gif', 'png', 'webp'):
        if os.path.exists(os.path.join(IMG, f'{base}.{e}')): b['f'] = f'{base}.{e}'; return
    try: d = subprocess.run(['curl.exe', '-sL', '-A', BROWSER, '-e', 'https://tibia.fandom.com/', '--max-time', '30', b['u']], capture_output=True, timeout=40).stdout
    except Exception: d = b''
    if tipo(d):
        f = f'{base}.{tipo(d)}'; open(os.path.join(IMG, f), 'wb').write(d); b['f'] = f
print(f'Baixando {len(nomes)} sprites...')
with ThreadPoolExecutor(6) as ex: list(ex.map(baixar, bosses.values()))
out = [{k: v for k, v in b.items() if k != 'u'} for b in bosses.values()]
open(os.path.join(AQUI, 'data', 'bosses.js'), 'w', encoding='utf-8').write('window.BOSSES=' + json.dumps(out, ensure_ascii=False) + ';')
dbg.write('\nEXEMPLOS: ' + json.dumps(out[:8], ensure_ascii=False)); dbg.close()
print(f'Pronto: {len(out)} bosses, {sum(1 for b in out if b["f"])} com sprite.')
