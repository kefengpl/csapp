import os
import subprocess
script_dir = os.path.dirname(os.path.abspath(__file__))
test_seqnums = ["{:02d}".format(elem) for elem in range(1, 17)]
for seqnum in test_seqnums[:16]:
    print(f"===============TEST{seqnum}===============")
    result = subprocess.run(["make", "test" + seqnum], 
                            capture_output=True, text=True, cwd=script_dir)
    print(result.stdout, end = "")
    print()
    ref_result = subprocess.run(["make", "rtest" + seqnum], 
                                capture_output=True, text=True, cwd=script_dir)
    print(ref_result.stdout, end = "")
