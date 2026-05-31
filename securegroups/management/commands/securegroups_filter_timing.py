from collections import defaultdict

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from securegroups.models import SmartGroup


def get_user_count(sg):
    """Count the users that run_smart_group_update would process, without running filters."""
    group = sg.group
    if sg.auto_group:
        states = group.authgroup.states.all()
        if states.exists():
            return User.objects.filter(profile__state__in=states).distinct().count()
        return User.objects.filter(profile__main_character__isnull=False).distinct().count()
    return group.user_set.count()


def parse_timing(timing_text):
    """Parse last_run_timing text into {description: duration} dict, skipping the Total line."""
    result = {}
    for line in timing_text.strip().splitlines():
        if line.startswith("Total:"):
            continue
        try:
            duration_str, desc = line.split("s  ", 1)
            result[desc.strip()] = float(duration_str.strip())
        except ValueError:
            continue
    return result


def build_desc_to_class(sg):
    """Map filter description -> filter class name for this smart group."""
    mapping = {}
    for f in sg.filters.all():
        try:
            mapping[f.filter_object.description] = type(f.filter_object).__name__
        except Exception:
            pass
    return mapping


def _print_timing_table(stdout, style, title, rows):
    width = 76
    stdout.write("")
    stdout.write("=" * width)
    stdout.write(style.SUCCESS(title))
    stdout.write("=" * width)
    stdout.write(f"  {'Label':<43} {'Runs':>4}  {'Total':>8}  {'Per User':>9}  {'Max/User':>9}")
    stdout.write("-" * width)
    for label, runs, total, per_user, max_per_user in sorted(rows, key=lambda r: r[2], reverse=True):
        stdout.write(
            f"  {label:<43} {runs:>4}  {total:>7.3f}s  {per_user:>8.4f}s  {max_per_user:>8.4f}s"
        )
    stdout.write("-" * width)


def build_rows(data):
    rows = []
    for label, entries in data.items():
        total_duration = sum(d for d, _ in entries)
        total_users = sum(u for _, u in entries)
        max_per_user = max((d / u if u else 0) for d, u in entries)
        per_user = total_duration / total_users if total_users else 0
        rows.append((label, len(entries), total_duration, per_user, max_per_user))
    return rows


class Command(BaseCommand):
    help = "Reports aggregate filter timing from stored last_run_timing data, slowest first."

    def add_arguments(self, parser):
        parser.add_argument(
            "--group",
            dest="group_name",
            default=None,
            help="Limit report to a single group by name.",
        )

    def handle(self, *args, **options):
        groups = SmartGroup.objects.filter(enabled=True).exclude(
            last_run_timing=""
        ).select_related("group", "group__authgroup")

        if options["group_name"]:
            groups = groups.filter(group__name=options["group_name"])

        if not groups.exists():
            self.stdout.write(self.style.WARNING(
                "No enabled smart groups with timing data found. Run the update task first."
            ))
            return

        aggregate = defaultdict(list)   # description -> [(duration, user_count)]
        class_aggregate = defaultdict(list)  # class name -> [(duration, user_count)]
        group_totals = {}

        for sg in groups:
            timings = parse_timing(sg.last_run_timing)
            if not timings:
                continue

            user_count = get_user_count(sg)
            desc_to_class = build_desc_to_class(sg)

            total = sum(timings.values())
            group_totals[sg.group.name] = (total, user_count)

            for desc, duration in timings.items():
                aggregate[desc].append((duration, user_count))
                class_name = desc_to_class.get(desc, "Unknown")
                class_aggregate[class_name].append((duration, user_count))

        if not aggregate:
            self.stdout.write(self.style.WARNING("No filter timing data could be parsed."))
            return

        _print_timing_table(
            self.stdout, self.style,
            "Filter Timings — by instance (slowest total first)",
            build_rows(aggregate),
        )

        _print_timing_table(
            self.stdout, self.style,
            "Filter Timings — by class (slowest total first)",
            build_rows(class_aggregate),
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Per-Group Totals (slowest per user first)"))
        self.stdout.write("-" * 76)
        self.stdout.write(f"  {'Per User':>9}  {'Total':>8}  {'Users':>6}  Group")
        self.stdout.write("-" * 76)
        for gname, (total, user_count) in sorted(
            group_totals.items(),
            key=lambda x: x[1][0] / x[1][1] if x[1][1] else 0,
            reverse=True,
        ):
            per_user = total / user_count if user_count else 0
            self.stdout.write(f"  {per_user:>8.4f}s  {total:>7.3f}s  {user_count:>6}  {gname}")
