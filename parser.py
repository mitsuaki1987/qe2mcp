class QEParser:
    def __init__(self):
        self.text        # ファイル全体
        self.lines       # 行ごとのリスト
        self.data = {   # 出力するJSON相当の辞書
            "program": {},
            "input": {},
            "structure_initial": {},
            "ionic_steps": [],
            "structure_final": {},
            "timing": {},
        }
        ...

    def parse(self, filename):
        self._load(filename)

        self._parse_program()
        self._parse_system()
        self._parse_ionic_steps()
        self._parse_timing()

        return self.data

    
    def _parse_program(self):
        ...

    def _parse_system(self):
        ...

    def _parse_ionic_steps(self):
        ...

    def _parse_timing(self):
        ...
