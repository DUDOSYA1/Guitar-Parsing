import subprocess
import sys
import os
import signal
import time

processes = []


def start(script):

    script_path = os.path.abspath(script)

    process = subprocess.Popen(
        [sys.executable, script_path],
        cwd=os.path.dirname(script_path)
    )

    processes.append(process)

    print(
        f"✅ Запущен: {script}"
    )

    return process


def stop(sig=None, frame=None):

    print("\nОстановка...")

    for process in processes:

        try:

            process.terminate()

        except:
            pass

    print("Все процессы остановлены")

    sys.exit()


if __name__ == "__main__":

    signal.signal(
        signal.SIGINT,
        stop
    )

    signal.signal(
        signal.SIGTERM,
        stop
    )

    try:

        # запуск обновления
        start("update.py")

        # запуск бота
        start("tg_bot.py")

        print(
            "\n🚀 Все сервисы запущены"
        )

        while True:

            for process in processes:

                # если процесс умер
                if process.poll() is not None:

                    print(
                        f"❌ Процесс завершился "
                        f"(код {process.returncode})"
                    )

            time.sleep(3)

    except Exception as e:

        print(
            f"Ошибка запуска: {e}"
        )

        stop()