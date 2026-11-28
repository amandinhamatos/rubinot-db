# Coleta charms (custos e efeitos), tabela de dificuldades do bestiário e criaturas com imagens.
# Uso: python coletar_charms.py   (na mesma pasta do index.html)
import json, re, os, time, subprocess, urllib.request, urllib.parse, html.parser
from concurrent.futures import ThreadPoolExecutor
API = 'https://tibia.fandom.com/api.php'
BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(AQUI, 'img', 'creatures'); os.makedirs(IMG, exist_ok=True)
Q = urllib.parse.quote
NOMES = ['Wound','Enflame','Poison','Freeze','Zap','Curse','Cripple','Parry','Dodge','Adrenaline Burst','Numb','Cleanse','Bless','Scavenge','Gut','Low Blow','Divine Wrath','Vampiric Embrace',"Void's Call",'Savage Blow','Fatal Hold','Overpower','Overflux','Carnage','Void Inversion']
DL = ['Harmless','Trivial','Easy','Medium','Hard','Challenging']

def api(**p):
    url = API + '?' + urllib.parse.urlencode(p) + '&format=json'
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': BROWSER}), timeout=40) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception: time.sleep(2)
    return {}

class T(html.parser.HTMLParser):
    def __init__(s): super().__init__(); s.t = []; s.r = None; s.c = None
    def handle_starttag(s, tag, a):
        if tag == 'table': s.t.append([])
        elif tag == 'tr' and s.t: s.r = []; s.t[-1].append(s.r)
        elif tag in ('td', 'th') and s.r is not None: s.c = []
        elif tag == 'img' and s.c is not None:
            d = dict(a); u = d.get('data-src') or d.get('src') or ''
            if u.startswith('http'): s.c.append('\x01' + u + '\x01')
    def handle_endtag(s, tag):
        if tag in ('td', 'th') and s.c is not None and s.r is not None:
            s.r.append(' '.join(''.join(s.c).split())); s.c = None
    def handle_data(s, d):
        if s.c is not None: s.c.append(d)

def linhas(pagina):
    h = api(action='parse', page=pagina, prop='text').get('parse', {}).get('text', {}).get('*', '')
    p = T(); p.feed(h)
    return [r for t in p.t for r in t if r]

def numeros(txt, minimo=0):
    return [int(n.replace(',', '')) for n, pct in re.findall(r'(\d[\d,]*)(\s*%)?', txt) if not pct and int(n.replace(',', '') or 0) >= minimo]

os.makedirs(os.path.join(AQUI, 'data'), exist_ok=True)
class R(list): pass
def limpa(row):
    r = R(' '.join(re.sub(r'\x01[^\x01]*\x01', '', c).split()) for c in row)
    r.imgs = [u for c in row for u in re.findall(r'\x01([^\x01]+)\x01', c)]
    return r
def tabelas(pagina):
    h = api(action='parse', page=pagina, prop='text', redirects=1).get('parse', {}).get('text', {}).get('*', '')
    p = T(); p.feed(h)
    return [[limpa(r) for r in t if r] for t in p.t]
def ach(row, nome, prefixo=True):
    for i, c in enumerate(row):
        x = c.strip().lower()
        if x == nome.lower() or (prefixo and x.startswith(nome.lower() + ' ')): return i
    return -1
TC, TB = tabelas('Charms'), tabelas('Bestiary')
print(f'Página Charms: {len(TC)} tabelas | página Bestiary: {len(TB)} tabelas')
with open(os.path.join(AQUI, 'data', 'debug_charms.txt'), 'w', encoding='utf-8') as f:
    for nome, TT in (('Charms', TC), ('Bestiary', TB)):
        for k, t in enumerate(TT):
            f.write(f'## {nome} tabela {k} ({len(t)} linhas)\n')
            for r in t[:40]: f.write(' | '.join(x[:60] for x in r) + '\n')
# 1) Charms (o nome pode estar em qualquer coluna; os custos podem estar nas linhas seguintes)
charms = {}
for t in TC:
    cur = None
    for r in t:
        hit = next(((n, ach(r, n)) for n in NOMES if ach(r, n) >= 0), None)
        if hit:
            cur = hit[0]
            if cur not in charms: charms[cur] = {'n': cur, 'c': [], 't': ' '.join(r[hit[1] + 1:])[:220], 'img': ''}
            nums = numeros(' '.join(r[hit[1] + 1:]), 100)
        elif cur: nums = numeros(' '.join(r), 100)
        else: continue
        if r.imgs and not charms[cur]['img']: charms[cur]['img'] = r.imgs[0]
        for v in nums:
            if len(charms[cur]['c']) < 3 and v not in charms[cur]['c']: charms[cur]['c'].append(v)
charms = {n: v for n, v in charms.items() if len(v['c']) == 3}
print(f'Charms com custo lido: {len(charms)} de {len(NOMES)}')
for n, v in charms.items(): print(f'  {n}: {v["c"]}')
# 2) Dificuldades do bestiário
diff, diffv = {}, {}
for t in TB:
    cur = None
    for r in t:
        a = r[0].lower() if r else ''
        d = next((x for x in DL if a.startswith(x.lower())), None)
        if d and d not in diff:
            cur = d; x = numeros(' '.join(r[2:]))
            if len(x) >= 4: diff[d] = {'k': x[:3], 'p': x[3]}
        elif a.startswith('very rare') and cur and cur not in diffv:
            x = numeros(' '.join(r[1:]))
            if len(x) >= 4: diffv[cur] = {'k': x[:3], 'p': x[3]}
print('Dificuldades lidas (kills 1/2/3 e pontos), comuns e Very Rare:')
for d in DL: print(f'  {d}: {diff.get(d)} | Very Rare: {diffv.get(d)}')
# 3) Criaturas
nomes = []
for cat in ('Creatures', 'Monsters'):
    cont = ''; m = []
    while True:
        j = api(action='query', list='categorymembers', cmtitle='Category:' + cat, cmlimit=500, cmnamespace=0, **({'cmcontinue': cont} if cont else {}))
        m += [x['title'] for x in j.get('query', {}).get('categorymembers', [])]
        cont = j.get('continue', {}).get('cmcontinue', '')
        if not cont: break
    print(f'Categoria {cat}: {len(m)} páginas')
    if m: nomes = m; break
def atk_comp(txt):
    # estima a composição do dano que a criatura causa, pelo texto de habilidades (aproximado)
    KW = [('Fire', r'fire|flame|burn|inferno|hellfire'), ('Earth', r'earth|poison|acid|thorn|swamp'), ('Energy', r'energy|electri|lightning|shock|storm'), ('Ice', r'\bice\b|frost|freez|cold|blizzard|avalanche'), ('Holy', r'holy|smite|divine'), ('Death', r'death|life ?drain|curse|wither|soul|shadow|necro')]
    w = {k: 0 for k in ('Physical', 'Fire', 'Energy', 'Earth', 'Ice', 'Death', 'Holy')}
    txt = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', txt)
    for it in re.split(r'\}\}|\{\{|,|\n|\*|<br ?/?>', txt):
        nums = [int(b) for a, b in re.findall(r'(\d+)\s*-\s*(\d+)', it)] + [int(x) for x in re.findall(r'up to\s*(\d+)', it, re.I)]
        if not nums: continue
        tipo_ = next((k for k, rx in KW if re.search(rx, it, re.I)), 'Physical')
        w[tipo_] += max(nums)
    tot = sum(w.values())
    return [round(100 * w[k] / tot) for k in ('Physical', 'Fire', 'Energy', 'Earth', 'Ice', 'Death', 'Holy')] if tot else None
cri = []
samp = []
for i in range(0, len(nomes), 40):
    j = api(action='query', prop='revisions', rvprop='content', rvslots='main', titles='|'.join(nomes[i:i+40]))
    for p in j.get('query', {}).get('pages', {}).values():
        t = p.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')
        d = re.search(r'\|\s*bestiarylevel\s*=\s*([A-Za-z]+)', t, re.I)
        c = re.search(r'\|\s*bestiaryclass\s*=\s*([^\n|]+)', t, re.I)
        if d and d.group(1).capitalize() in DL:
            mm = {k.lower(): int(v) for k, v in re.findall(r'\|\s*(physical|fire|energy|earth|ice|death|holy)DmgMod\s*=\s*(-?\d+)', t, re.I)}
            dm = [mm.get(k) for k in ('physical', 'fire', 'energy', 'earth', 'ice', 'death', 'holy')]
            dm = None if all(v is None for v in dm) else [100 if v is None else v for v in dm]
            ab = re.search(r'\|\s*abilities\s*=\s*(.*?)(?=\n\|\s*[A-Za-z_]+\s*=|\n\}\})', t, re.I | re.S)
            at = atk_comp(ab.group(1)) if ab else None
            if len(samp) < 4 or p['title'] in ('Stonerefiner', 'Werelion'): samp.append(p['title'] + '\nABILITIES: ' + (ab.group(1)[:500] if ab else 'nao encontrado') + '\nAT: ' + str(at) + '\n' + '\n'.join(l for l in t.splitlines() if 'mod' in l.lower())[:300])
            if False: samp.append(p['title'] + '\n' + '\n'.join(l for l in t.splitlines() if 'mod' in l.lower() or 'resist' in l.lower())[:800])
            cri.append({'n': p['title'], 'cl': c.group(1).strip() if c else '', 'd': d.group(1).capitalize(), 'o': (re.search(r'\|\s*occurrence\s*=\s*([^\n|]+)', t, re.I) or [0, ''])[1].strip().title(), 'f': '', 'dm': dm, 'at': at})
cri.sort(key=lambda x: x['n'])
print(f'Criaturas com dados de fraqueza elemental: {sum(1 for x in cri if x.get("dm"))} de {len(cri)} | com estimativa de ataque: {sum(1 for x in cri if x.get("at"))}')
open(os.path.join(AQUI, 'data', 'debug_creature.txt'), 'w', encoding='utf-8').write('\n\n'.join(samp))
print(f'Criaturas no bestiário: {len(cri)}')
# 4) Imagens (via curl, que já funcionou)
def tipo(d):
    if d[:4] == b'GIF8': return 'gif'
    if d[:4] == b'\x89PNG': return 'png'
    if d[:4] == b'RIFF' and d[8:12] == b'WEBP': return 'webp'
    return None
U = {}
tit = [f'File:{c["n"]}.{e}' for c in cri for e in ('gif', 'png')]
for i in range(0, len(tit), 50):
    j = api(action='query', prop='imageinfo', iiprop='url', titles='|'.join(tit[i:i+50]))
    for p in j.get('query', {}).get('pages', {}).values():
        if p.get('imageinfo'): U[p['title'].replace('_', ' ').lower()] = p['imageinfo'][0]['url']
def baixar(c):
    base = re.sub(r'[^A-Za-z0-9]+', '_', c['n']).lower().strip('_')
    for e in ('gif', 'png', 'webp'):
        if os.path.exists(os.path.join(IMG, f'{base}.{e}')): c['f'] = f'{base}.{e}'; return
    for e in ('gif', 'png'):
        u = U.get(f'file:{c["n"]}.{e}'.lower())
        if not u: continue
        try: d = subprocess.run(['curl.exe', '-sL', '-A', BROWSER, '-e', 'https://tibia.fandom.com/', '--max-time', '30', u], capture_output=True, timeout=40).stdout
        except Exception: d = b''
        if tipo(d):
            f = f'{base}.{tipo(d)}'; open(os.path.join(IMG, f), 'wb').write(d); c['f'] = f; return
print(f'Baixando imagens de {len(cri)} criaturas...')
with ThreadPoolExecutor(6) as ex: list(ex.map(baixar, cri))
os.makedirs(os.path.join(AQUI, 'data'), exist_ok=True)
IMGC = os.path.join(AQUI, 'img', 'charms'); os.makedirs(IMGC, exist_ok=True)
for v in charms.values():
    u = v.pop('img', '')
    if not u: continue
    try: d = subprocess.run(['curl.exe', '-sL', '-A', BROWSER, '-e', 'https://tibia.fandom.com/', '--max-time', '30', u], capture_output=True, timeout=40).stdout
    except Exception: d = b''
    if tipo(d):
        f = re.sub(r'[^A-Za-z0-9]+', '_', v['n']).lower() + '.' + tipo(d)
        open(os.path.join(IMGC, f), 'wb').write(d); v['f'] = f
print(f'Imagens de charms salvas: {sum(1 for v in charms.values() if v.get("f"))} de {len(charms)}')
open(os.path.join(AQUI, 'data', 'charms.js'), 'w', encoding='utf-8').write('window.CHARMS=' + json.dumps(list(charms.values()), ensure_ascii=False) + ';window.BEST=' + json.dumps({'diff': diff, 'diffv': diffv, 'creatures': cri}, ensure_ascii=False) + ';')
print(f'Pronto: {len(charms)} charms, {len(cri)} criaturas, {sum(1 for c in cri if c["f"])} com imagem.')
