"""Month arithmetic on the county's 'YYYYMM' sale-date strings."""


def months_back(yyyymm, n):
    """'202601' two months back is '202511'. The old f"{int(mm)-2:02d}" produced '2026-1' and
    '202600' for January and February snapshots, so string comparison against it marked only
    the new year's sales as recent (found 2026-10-18)."""
    y, m = int(yyyymm[:4]), int(yyyymm[4:6])
    m -= n
    while m < 1:
        m += 12
        y -= 1
    return f"{y:04d}{m:02d}"
