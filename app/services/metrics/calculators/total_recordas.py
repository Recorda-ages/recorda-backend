from app.services.metrics.context import MetricsContext


class TotalRecordasCalculator:
    def calculate(self, context: MetricsContext) -> int:
        return len(context.recordas)
