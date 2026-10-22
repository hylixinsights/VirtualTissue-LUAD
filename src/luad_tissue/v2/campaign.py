"""Durable whole-campaign request ceiling, including failed/unknown attempts."""
import json,os
from pathlib import Path
from ..io import canonical,fingerprint
from ..providers import BudgetExhausted


class CampaignBudget:
    def __init__(self,directory,limit):
        if type(limit) is not int or limit<1:raise ValueError("Positive campaign cap required")
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.limit=limit
        self.ledger=self.directory/'usage.jsonl'
        self.lock=self.directory/'usage.lock'
        cap=self.directory/'authorization.json'
        if cap.exists():
            if json.loads(cap.read_text())["max_requests"]!=limit:raise ValueError("Campaign cap is immutable")
        else:
            with cap.open('x',encoding='utf8') as f:
                json.dump(dict(max_requests=limit,scope="LUAD biological/mechanical calibration and Jev experiments; failures count"),f)

    def entries(self):
        return [json.loads(line) for line in self.ledger.read_text(encoding='utf8').splitlines()] if self.ledger.exists() else []

    def reserve(self,body,run):
        try:fd=os.open(self.lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        except FileExistsError:raise RuntimeError("Campaign ledger is locked; review before retrying") from None
        try:
            entries=self.entries()
            if len(entries)>=self.limit:raise BudgetExhausted("Whole-campaign request ceiling reached")
            entry=dict(attempt=len(entries)+1,run=run,request_hash=fingerprint(body),status="reserved_before_transport")
            with self.ledger.open('a',encoding='utf8',newline='\n') as f:
                f.write(canonical(entry).decode()+'\n');f.flush();os.fsync(f.fileno())
            return entry['attempt']
        finally:
            os.close(fd);self.lock.unlink()

    def wrap(self,transport,run):
        def call(body):
            self.reserve(body,run)
            return transport(body)
        return call
