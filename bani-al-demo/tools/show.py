import json,sys,pathlib,re
sys.stdout.reconfigure(encoding='utf-8')
d=pathlib.Path('C:/dev/bani-al-demo/clients')/sys.argv[1]/'ig'
p=json.loads((d/'profile.json').read_text(encoding='utf-8'))
print(p['full_name'],'|',p['biography'].replace('\n',' / '),'|',p.get('category'),p['followers'])
if (d/'has_site.txt').exists(): print('HAS_SITE',(d/'has_site.txt').read_text())
for i,x in enumerate(json.loads((d/'posts.json').read_text(encoding='utf-8')),1):
    print(i,x.get('code'),x.get('type')[0],len(x['files']),'|',(x.get('caption') or '').replace('\n',' ')[:int(sys.argv[2]) if len(sys.argv)>2 else 160])
print('H',[(h.get('title'),len(h['stories'])) for h in json.loads((d/'highlights.json').read_text(encoding='utf-8'))])
