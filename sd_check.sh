#!/bin/bash
for d in sda sdb; do
  echo "===== /dev/$d ====="
  mkdir -p /mnt/chk_$d
  if mount -o ro /dev/$d /mnt/chk_$d 2>&1; then
    ls -la /mnt/chk_$d | head -40
    echo "--- looking for armbian_first_run ---"
    ls -la /mnt/chk_$d/boot/armbian_first_run* 2>/dev/null
    ls -la /mnt/chk_$d/armbian_first_run* 2>/dev/null
    umount /mnt/chk_$d 2>/dev/null
  else
    echo "mount failed"
  fi
done
