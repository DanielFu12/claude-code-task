"""整篇录音“多录几条挑最好的一条”（仍是整篇一次合成，不拼接）：
python3 src/take_rolls.py WORK N      → 并行合成 N 条到 WORK/vo_take/roll_<key>_<k>.wav
python3 src/take_rolls.py WORK pick 文件  → 把选中的那条设为正式录音（复制到 take 路径）
挑选：逐条跑 voice_build（对齐校验）+ check_vo（逐句语音识别），比差异数与最低相似度（见 src/eval_rolls.sh）。"""
import os, sys, shutil, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts_take as T
work = sys.argv[1]
if sys.argv[2] == 'pick':
    src = sys.argv[3]; dst = T.take_path(work)
    shutil.copy(src, dst); shutil.copy(src[:-4] + '.json', dst[:-4] + '.json'); print('take ←', src)
else:
    n = int(sys.argv[2]); k0 = T.key(T.take_text())
    outs = [os.path.join(work, 'vo_take', f'roll_{k0}_{i}.wav') for i in range(n)]
    with cf.ThreadPoolExecutor(n) as ex:
        for w in ex.map(lambda o: T.synth(T.take_text(), o), outs): print('done', w, flush=True)
