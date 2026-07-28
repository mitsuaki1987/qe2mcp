class QEParser:
    def __init__(self):
        self.text        # ファイル全体
        self.lines       # 行ごとのリスト
        self.data        # 出力するJSON相当の辞書
        ...

    def parse(self, filename):
        ...

    def _parse_program(self):
        ...

    def _parse_system(self):
        ...

    def _parse_ionic_steps(self):
        ...

    def _parse_timing(self):
        ...
