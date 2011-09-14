global hist
#print "Looking at", filepath
for kk in tags.keys():
  if not tags[kk] or kk.find(".") < 1:
    continue
  if hist.has_key(kk):
    hist[kk] += 1
  else:
    hist[kk] = 1
