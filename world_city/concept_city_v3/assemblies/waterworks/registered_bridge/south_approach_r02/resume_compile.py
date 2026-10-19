import author
original=author.write
def safe_write(p,d):
 if p.exists():
  assert author.read(p)==d, str(p)
 else: original(p,d)
author.write=safe_write
author.main()
