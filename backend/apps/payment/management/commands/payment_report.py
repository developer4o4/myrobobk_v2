from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from apps.payment.utils import get_daily_stats, find_stuck_transactions
from apps.payment.models import PaymeTransaction


class Command(BaseCommand):
    help = "Generate payment statistics report"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Report date (YYYY-MM-DD format). Default: today",
        )
        parser.add_argument(
            "--range",
            type=int,
            help="Report for last N days",
        )

    def handle(self, *args, **options):
        date_str = options.get("date")
        range_days = options.get("range")

        self.stdout.write(self.style.SUCCESS("\n📊 PAYMENT STATISTICS REPORT\n"))
        self.stdout.write("=" * 60)

        if range_days:
            self._report_range(range_days)
        elif date_str:
            self._report_date(date_str)
        else:
            self._report_date(None)

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("\n✅ Report generated\n"))

    def _report_date(self, date_str):
        if date_str:
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR(f"Invalid date format: {date_str}")
                )
                return
        else:
            date = timezone.now().date()

        stats = get_daily_stats(date)

        self.stdout.write(f"\n📅 Date: {stats['date']}\n")

        # Completed
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ COMPLETED: {stats['completed']['count']} transactions"
            )
        )
        self.stdout.write(
            f"   Total: {stats['completed']['total_som']:,.2f} som\n"
        )

        # Pending
        self.stdout.write(
            self.style.WARNING(
                f"⏳ PENDING: {stats['pending']['count']} transactions"
            )
        )
        self.stdout.write(f"   Total: {stats['pending']['total_som']:,.2f} som\n")

        # Canceled
        self.stdout.write(
            self.style.ERROR(f"❌ CANCELED: {stats['canceled']['count']} transactions")
        )
        self.stdout.write(f"   Total: {stats['canceled']['total_som']:,.2f} som\n")

        # Summary
        total_income = stats["completed"]["total_som"]
        self.stdout.write(
            self.style.SUCCESS(f"\n💰 TOTAL INCOME: {total_income:,.2f} som")
        )

        # Check for stuck transactions
        stuck = find_stuck_transactions()
        if stuck:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  WARNING: {len(stuck)} stuck transactions (>24h pending)"
                )
            )
            for tx_id in stuck:
                self.stdout.write(f"   - {tx_id}")

    def _report_range(self, days):
        self.stdout.write(f"\n📊 Report for last {days} days:\n")

        total_income = 0
        total_transactions = 0

        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            stats = get_daily_stats(date)

            completed = stats["completed"]["total_som"]
            count = stats["completed"]["count"]

            if count > 0:
                self.stdout.write(
                    f"{date}: {count:3d} txs | {completed:10,.2f} som"
                )
                total_income += completed
                total_transactions += count

        self.stdout.write("\n" + "-" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📈 Total: {total_transactions} transactions | {total_income:,.2f} som\n"
            )
        )
