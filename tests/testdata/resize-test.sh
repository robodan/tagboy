#!/bin/bash
# Create test sized versions of images in a subdirectory

# different width specs depending on horizontal or vertical images
HWIDTH=320
VWIDTH=240
DIR=${HWIDTH}x${VWIDTH}

# the new file extension determines output file type
EXT="jpg"
ARGS="-quality 60"
COPYRIGHT='Test data'

abort() {
  echo "$@"
  exit
}

[[ -d "$DIR" ]] || mkdir -v "$DIR"
[[ -d "$DIR" ]] || abort "Unable to create '$DIR'"

for f ; do			# for all file on command line
  base=${f%.???}
  dest="$DIR/$base.$EXT"
  [[ -s "$dest" ]] && continue # already done
  geom=`identify "$f" | cut -f3 -d' '`
  width=`echo "$geom" | cut -f1 -d'x'`
  height=`echo "$geom" | cut -f2 -d'x'`
  if [[ -z "$width" || -z "$height" ]] ; then
      echo "Error parsing size of '$f'"
      continue
  fi
  if [[ $width -gt $height ]] ; then # image is horizontal (landscape)
      if [[ $width -gt $HWIDTH ]] ; then
	  convert "$f" -resize $HWIDTH $ARGS -comment "$COPYRIGHT" "$dest"
      else			# small image, just make a link
	  ln "$f" "$dest"
      fi
  else				# image is vertical
      if [[ $width -gt $VWIDTH ]] ; then
	  convert "$f" -resize $VWIDTH $ARGS -comment "$COPYRIGHT" "$dest"
      else			# small image, just make a link
	  ln "$f" "$dest"
      fi
  fi
  #echo "'$base' $width $height"
  identify "$f" "$dest"
done
