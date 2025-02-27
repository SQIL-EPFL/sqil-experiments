import subprocess
import time


def run_script(max_runs=2):
    for i in range(max_runs):
        try:
            print(f"Run {i + 1} of {max_runs}")
            # 実行するスクリプトを呼び出す
            subprocess.run(["python", "CW_onetone_run_no_flux.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred during run {i + 1}: {e}")

        if i < max_runs - 1:  # 最後の実行の後は待機しない
            print("Waiting for 30 minutes...")
            time.sleep(20 * 60)


if __name__ == "__main__":
    run_script(max_runs=24)
