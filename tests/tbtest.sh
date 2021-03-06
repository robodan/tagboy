#!/bin/bash
# Test tb-* scripts
# Nothing fancy here.  Mainly checking for crashes and missing output.

# Usage: tbtest.sh

# Print message and exit
abort() {
  echo "$@"
  exit 1
}

errors=0
# Display an error
error() {
  echo "$@"
  (( errors += 1 ))
}

tmp_dir="/tmp/${LOGNAME}_tb-test"
[[ -d "$tmp_dir" ]] || mkdir "$tmp_dir"
[[ -d "$tmp_dir" ]] || abort "Unable to access: $tmp_dir"
[[ -r "tagboy/tbcmd.py" ]] && tdir="./" ||  tdir="../"
[[ -x "$tdir/tagboy" ]] || abort "Unable to run  $tdir/tagboy"
testdata="$tdir/tests/testdata"
[[ -d "$testdata" ]] || abort "Unable to access testdata in: $testdata"

Test_tb-gpspos() {
    out="$tmp_dir/Test_tb-gpspos.out"
    $tdir/tb-gpspos "$testdata" --iname '*.jpg' > "$out"
    ret=$?
    [[ "$ret" = 0 ]] || error "Expected return status of 0, not $ret"
    grep -q "IMAG0166.jpg" $out || error "Didn't find IMAG0166.jpg in $out"
    grep -q "IMAG0160.jpg" $out || error "Didn't find IMAG0160.jpg in $out"
    grep -q "butterfly-tagtest.jpg" $out || error "Didn't find butterfly-tagtest.jpg in $out"
}

Test_tb-tagcount() {
    out="$tmp_dir/Test_tb-tagcount.out"
    $tdir/tb-tagcount "$testdata" --iname '*.jpg' > "$out"
    ret=$?
    [[ "$ret" = 0 ]] || error "Expected return status of 0, not $ret"
    lines=`wc -l "$out" | cut -f1 -d' '`
    [[ "$lines" -gt 360 ]] || error "Too few lines in $out"
}

Test_tb-tagdiff() {
    out="$tmp_dir/Test_tb-tagdiff.out"
    $tdir/tb-tagdiff "$testdata" --iname '*.jpg' > "$out"
    ret=$?
    [[ "$ret" = 0 ]] || error "Expected return status of 0, not $ret"
    lines=`wc -l "$out" | cut -f1 -d' '`
    [[ "$lines" -gt 420 ]] || error "Too few lines in $out"
}

main() {
    echo "Test_tb-gpspos" ; Test_tb-gpspos || error "--- gpspos exit error"
    echo "Test_tb-tagcount" ; Test_tb-tagcount || error "--- tagcount exit error"
    echo "Test_tb-tagdiff" ; Test_tb-tagdiff || error "--- tagdiff exit error"
}

main "$@"

echo "Encountered $errors errors"
if [[ "$errors" = 0 ]] ; then
  rm -rf "$tmp_dir"
  exit 0
else
  echo "Leaving $tmp_dir for debugging"
  exit 1
fi
