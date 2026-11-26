# Baixa a lista de itens e as imagens da TibiaWiki para o seu site.
# Uso: python coletar_itens.py   (pode ser interrompido e rodado de novo; ele continua de onde parou)
import json, re, os, time, urllib.request, urllib.parse, urllib.error
from concurrent.futures import ThreadPoolExecutor

API = 'https://tibia.fandom.com/api.php'
UA = {'User-Agent': 'Mozilla/5.0 RubinOT-Database/1.1 (uso pessoal)', 'Referer': 'https://tibia.fandom.com/'}
AQUI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(AQUI, 'img', 'items')
os.makedirs(IMG, exist_ok=True)
Q = urllib.parse.quote
# (slot do site, [nomes possíveis da categoria na wiki]). Usa o primeiro nome que tiver itens.
CATS = [
    ('Trinket', ['Light Sources', 'Light Source']), ('Utility', ['Tools']),
    ('Helmet', ['Helmets']), ('Armor', ['Armors']), ('Legs', ['Legs']), ('Boots', ['Boots']),
    ('Amulet', ['Amulets and Necklaces']), ('Ring', ['Rings']),
    ('Shield/Livro', ['Shields']), ('Shield/Livro', ['Spellbooks']), ('Shield/Livro', ['Quivers']),
    ('Backpack', ['Backpacks']),
    ('Weapon', ['Sword Weapons', 'Swords', 'Sword']), ('Weapon', ['Axe Weapons', 'Axes', 'Axe']),
    ('Weapon', ['Club Weapons', 'Clubs', 'Club']), ('Weapon', ['Distance Weapons']),
    ('Weapon', ['Wands']), ('Weapon', ['Rods']),
    ('Weapon', ['Fist Fighting Weapons', 'Fist Weapons']),
]
erros = [0]
import subprocess
BROWSER = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
EXTS = ('gif', 'png', 'webp', 'jpg')
def tipo(d):
    if not d: return None
    if d[:4] == b'GIF8': return 'gif'
    if d[:4] == b'\x89PNG': return 'png'
    if d[:4] == b'RIFF' and d[8:12] == b'WEBP': return 'webp'
    if d[:2] == b'\xff\xd8': return 'jpg'
    return None
def ok(d): return tipo(d) is not None
def _urllib(u, ref):
    h = {'User-Agent': BROWSER, 'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8'}
    if ref: h['Referer'] = 'https://tibia.fandom.com/'
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=h), timeout=30) as r: return r.read()
    except Exception: return None
def m_urllib(u): return _urllib(u, False)
def m_urllib_ref(u): return _urllib(u, True)
def m_curl(u):
    try: return subprocess.run(['curl.exe', '-sL', '-A', BROWSER, '-e', 'https://tibia.fandom.com/', '--max-time', '30', u], capture_output=True, timeout=40).stdout
    except Exception: return None
METODOS = [('urllib', m_urllib), ('urllib com referer', m_urllib_ref), ('curl', m_curl)]
MET = [None]

def get(url, binary=False):
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                d = r.read()
                return d if binary else d.decode('utf-8')
        except urllib.error.HTTPError as e:
            if erros[0] < 3:
                erros[0] += 1
                print(f'  [aviso] HTTP {e.code} em {url[:90]}')
            if 400 <= e.code < 500: return None
            time.sleep(2)
        except Exception as e:
            time.sleep(2)
    return None

def membros(cat):
    out, cont = [], ''
    while True:
        d = get(f"{API}?action=query&list=categorymembers&cmtitle={Q('Category:' + cat)}&cmlimit=500&cmnamespace=0&format=json{cont}")
        if not d: break
        j = json.loads(d)
        out += [m['title'] for m in j['query']['categorymembers']]
        if 'continue' in j: cont = '&cmcontinue=' + Q(j['continue']['cmcontinue'])
        else: break
    return out

def stats(titulos):
    res = {}
    for i in range(0, len(titulos), 40):
        d = get(f"{API}?action=query&prop=revisions&rvprop=content&rvslots=main&format=json&titles={Q('|'.join(titulos[i:i+40]))}")
        if not d: continue
        for p in json.loads(d)['query']['pages'].values():
            t = p.get('revisions', [{}])[0].get('slots', {}).get('main', {}).get('*', '')
            lv = re.search(r'\|\s*levelrequired\s*=\s*(\d+)', t, re.I)
            ar = re.search(r'\|\s*arm\s*=\s*(\d+)', t, re.I)
            g = lambda k: re.sub(r'\[\[|\]\]|<[^>]*>', '', (re.search(r'\|\s*' + k + r'\s*=\s*([^\n|]*)', t, re.I) or [0, ''])[1]).strip()
            res[p['title']] = {'l': int(lv.group(1)) if lv else None, 'a': int(ar.group(1)) if ar else None, 'ak': g('attack'), 'df': g('defense'), 'im': g('imbueslots'), 'at': g('attrib'), 'rs': g('resist'), 'vo': g('vocrequired')}
    return res

def urls_imagens(nomes):
    res = {}
    tit = [f'File:{n}.{e}' for n in nomes for e in ('gif', 'png')]
    for i in range(0, len(tit), 50):
        d = get(f"{API}?action=query&prop=imageinfo&iiprop=url&format=json&titles={Q('|'.join(tit[i:i+50]))}")
        if not d: continue
        for p in json.loads(d).get('query', {}).get('pages', {}).values():
            if p.get('imageinfo'): res[p['title'].replace('_', ' ').lower()] = p['imageinfo'][0]['url']
    return res

JUNK = re.compile(r'Products by|Weapons$|^(Armors|Boots|Helmets|Legs|Rings|Shields|Backpacks|Wands|Rods|Quivers|Spellbooks|Amulets and Necklaces)$')
itens = {}
for slot, nomes in CATS:
    achou = False
    for c in nomes:
        m = membros(c)
        if m:
            print(f'{c}: {len(m)} itens')
            for n in m:
                if ':' not in n: itens.setdefault(n, slot)
            achou = True
            break
    if not achou:
        print(f'{nomes[0]}: VAZIA (tentei {", ".join(nomes)})')
for n in ['Sun Catcher', 'Lit Torch', 'Starlight Vial', 'Moon Mirror', 'Black Jade Cobra']: itens[n] = 'Trinket'
for n in ['Squeezing Gear of Girlpower', 'Blessed Wooden Stake', 'Obsidian Knife', 'Whacking Driller of Fate']: itens[n] = 'Utility'
for n in ['Werewolf Amulet', 'Enchanted Werewolf Amulet']: itens[n] = 'Amulet'
itens['Bounty Talisman'] = 'Utility'
for n in ['Arrow','Poison Arrow','Burst Arrow','Flaming Arrow','Shiver Arrow','Earth Arrow','Onyx Arrow','Diamond Arrow','Crystalline Arrow','Tarsal Arrow','Bolt','Power Bolt','Infernal Bolt','Prismatic Bolt','Drill Bolt','Piercing Bolt','Spectral Bolt','Vortex Bolt']: itens[n] = 'Ammo'
for n in ['Great Fireball Rune','Avalanche Rune','Stone Shower Rune','Thunderstorm Rune','Sudden Death Rune','Energy Wall Rune','Fire Wall Rune','Energy Bomb Rune','Fire Bomb Rune','Poison Wall Rune','Poison Bomb Rune']: itens[n] = 'Rune'
nomes = sorted(itens)
print('Lendo level e armor...')
st = stats(nomes)
print('Procurando endereços das imagens...')
U = urls_imagens(nomes)
print(f'{len(U)} imagens encontradas. Testando como baixar...')
teste = next(iter(U.values()), None)
for nome, fn in METODOS:
    if teste and ok(fn(teste)):
        print('Método que funcionou:', nome)
        MET[0] = fn
        break
if not MET[0]:
    print('Os métodos simples foram bloqueados pela wiki. Tentando com um navegador de verdade (Chromium)...')
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None
        print('Falta instalar o navegador do script. Rode estes 2 comandos e depois rode este script de novo:')
        print('    pip install playwright')
        print('    python -m playwright install chromium')
    if sync_playwright:
        pares = []
        for n in nomes:
            base = re.sub(r'[^A-Za-z0-9]+', '_', n).lower().strip('_')
            if any(os.path.exists(os.path.join(IMG, f'{base}.{e}')) for e in EXTS): continue
            for e in ('gif', 'png'):
                u = U.get(f'file:{n}.{e}'.replace('_', ' ').lower())
                if u:
                    pares.append((u, os.path.join(IMG, base)))
                    break
        print(f'Baixando {len(pares)} imagens pelo navegador (pode levar 10 a 15 minutos; pode interromper e rodar de novo)...')
        feitas = 0
        with sync_playwright() as p:
            nav = p.chromium.launch()
            pg = nav.new_context(user_agent=BROWSER).new_page()
            for i, (u, caminho) in enumerate(pares):
                try:
                    r = pg.goto(u, timeout=30000)
                    d = r.body() if r and r.ok else None
                    if ok(d):
                        open(caminho + '.' + tipo(d), 'wb').write(d)
                        feitas += 1
                    elif erros[0] < 3:
                        erros[0] += 1
                        print(f'  [aviso] resposta {r.status if r else "?"}, início do conteúdo: {d[:16] if d else None}')
                except Exception as ex:
                    if erros[0] < 3:
                        erros[0] += 1
                        print('  [aviso]', str(ex)[:100])
                if i == 5 and feitas == 0:
                    print('As 6 primeiras imagens falharam; parando para não perder tempo. Me mande um print desta tela.')
                    break
                if (i + 1) % 100 == 0: print(f'  {i + 1}/{len(pares)} (salvas: {feitas})')
            nav.close()

def baixar(n):
    base = re.sub(r'[^A-Za-z0-9]+', '_', n).lower().strip('_')
    for ext in EXTS:
        f = f'{base}.{ext}'
        if os.path.exists(os.path.join(IMG, f)): return f
    for ext in ('gif', 'png'):
        u = U.get(f'file:{n}.{ext}'.replace('_', ' ').lower())
        if not u: continue
        d = MET[0](u) if MET[0] else None
        if ok(d):
            f = f'{base}.{tipo(d)}'
            open(os.path.join(IMG, f), 'wb').write(d)
            return f
    return ''

with ThreadPoolExecutor(6) as ex:
    arqs = list(ex.map(baixar, nomes))
cat = []
for n, f in zip(nomes, arqs):
    if not f and JUNK.search(n): continue
    x = st.get(n, {})
    cat.append({'n': n, 's': itens[n], 'f': f, 'l': x.get('l'), 'a': x.get('a'), 'ak': x.get('ak', ''), 'df': x.get('df', ''), 'im': x.get('im', ''), 'at': x.get('at', ''), 'rs': x.get('rs', ''), 'vo': x.get('vo', '')})
os.makedirs(os.path.join(AQUI, 'data'), exist_ok=True)
open(os.path.join(AQUI, 'data', 'items.js'), 'w', encoding='utf-8').write('window.CATALOG=' + json.dumps(cat, ensure_ascii=False) + ';')
sem = [c['n'] for c in cat if not c['f']]
print(f'Pronto: {len(cat)} itens, {len(cat) - len(sem)} com imagem, {len(sem)} sem imagem.')
if sem: print('Exemplos sem imagem:', ', '.join(sem[:8]))
