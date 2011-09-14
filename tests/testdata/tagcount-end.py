global hist
for kk in sorted(hist.keys()):
  print "%60s: %d" % (kk, hist[kk])
print "Looked at %d files" % filecount
