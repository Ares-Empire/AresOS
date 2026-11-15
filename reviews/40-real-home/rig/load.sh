#!/bin/bash
# Rig tool: average GPU utilisation/power and the game's CPU and memory over about 6 s. usage: load.sh <label>
pid=$(pgrep -f 'net.fabricmc.devlaunchinjector.Main' | head -1)
t0=$(awk '{print $14+$15}' /proc/$pid/stat); s0=$(date +%s.%N)
gpu=0; pw=0; n=0
for i in 1 2 3 4 5 6; do
  read -r u p <<<"$(nvidia-smi --query-gpu=utilization.gpu,power.draw --format=csv,noheader,nounits | tr -d ',')"
  gpu=$(echo "$gpu + $u" | bc -l); pw=$(echo "$pw + $p" | bc -l); n=$((n+1)); sleep 1
done
t1=$(awk '{print $14+$15}' /proc/$pid/stat); s1=$(date +%s.%N)
cpu=$(echo "($t1 - $t0) / $(getconf CLK_TCK) / ($s1 - $s0) * 100" | bc -l)
rss=$(awk '/VmRSS/{print int($2/1024)}' /proc/$pid/status)
gmem=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | awk -F', ' -v p=$pid '$1==p{print $2}')
printf '%-34s GPU %5.1f %%  %5.1f W   game CPU %6.1f %% of one core   RSS %s MiB   GPU mem %s MiB\n' "$1" "$(echo "$gpu/$n" | bc -l)" "$(echo "$pw/$n" | bc -l)" "$cpu" "$rss" "${gmem:-?}"
