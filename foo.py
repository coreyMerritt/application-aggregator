import time
import langid

langid.set_languages(['en', 'es', 'fr'])

start = time.time()
for _ in range(100):
  langid.classify("Senior Software Engineer")
print("Time:", time.time() - start)

