from tutorial.package2.module2 import q as q_from_module2
from scrapers.parse_cbr import main as qqq
print(f"init module1, we have __name__={__name__}. Also we imported q from module2: {q_from_module2}")
#qqq()
q = "module1"
