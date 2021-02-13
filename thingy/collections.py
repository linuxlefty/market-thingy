from __future__ import annotations
import re
from thingy.edgar.financials import FinancialInfo
from typing import Union, Optional
from dataclasses import dataclass


@dataclass
class Date:
    year: int
    quarter: int

    def __lt__(self, date: Date):
        return (self.year, self.quarter) < (date.year, date.quarter)


class FallThruDict(dict):
    def __init__(self, source: FinancialInfo):
        self._months = source.months
        self._factor = 1

        if self._months:
            self._factor = source.months / 3

        super().__init__(source.map)

    def __getitem__(self, keys: Union[list, str]) -> float:
        if isinstance(keys, str):
            keys = [keys]

        # Look up by key
        key_results = [sum(element.values) / self._factor
                       for key in keys
                       if (element := dict.get(self, key))]
        # Look up by label
        label_results = [sum(element.values) / self._factor
                         for element in self.values()
                         if (set(label.lower() for label in element.labels)
                             & set(label.lower() for label in keys))]

        results = key_results + label_results

        if not results:
            # Key not found
            raise KeyError(keys)

        for result in results:
            if result:
                # Non-zero value found
                return result

        # Welp, we got a zero value, but at least it is something
        return results[-1]

    def __contains__(self, keys: Union[list, str]) -> bool:
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            if key in self.keys():
                return True

        for element in self.values():
            if (set(label.lower() for label in element.labels)
                    & set(label.lower() for label in keys)):
                return True

        return False

    def get(self, *keys: list, default: Optional[float] = None) -> Optional[float]:
        if keys in self:
            return self[keys]
        return default

    def get_all(self, *keys: list) -> list:
        return [
            value for key in keys
            if (value := self.get(key)) is not None
        ]

    def search(self, *patterns: str) -> list:
        results = list()
        labels = (label for element in self.values() for label in element.labels)

        for pattern in patterns:
            results.extend(self[label] for label in labels
                           if re.match(pattern, label, re.IGNORECASE))
            results.extend(self[key] for key in self
                           if re.match(pattern, key, re.IGNORECASE))

        return results


@dataclass(frozen=True)
class Report:
    balance_sheet: FallThruDict
    cash_flow: FallThruDict
    income_statements: FallThruDict

    @classmethod
    def new(cls, filing) -> Report:
        return cls(
            balance_sheet=FallThruDict(
                cls.get_recent_quarterly_report(filing.get_balance_sheets().reports)),
            cash_flow=FallThruDict(
                cls.get_recent_quarterly_report(filing.get_cash_flows().reports)),
            income_statements=FallThruDict(
                cls.get_recent_quarterly_report(filing.get_income_statements().reports)))

    @staticmethod
    def get_recent_quarterly_report(reports: list) -> FinancialInfo:
        for months in (3, 6, 9, None):
            selected_reports = [(report.date, idx)
                                for idx, report in enumerate(reports)
                                if report.months == months]
            if selected_reports:
                date, idx = max(selected_reports)
                return reports[idx]
        breakpoint()
        raise ValueError('Not able to find any reports')
