"""実行入口：python src/main.py"""
from app import main

# このファイルを直接実行したときだけmainを呼ぶ。
# 他のファイルからimportした場合は__name__がモジュール名になるので、勝手に起動しない。
if __name__ == "__main__":
    main()
