import pytest

from src.shared.types import PaginationMeta


@pytest.mark.parametrize(
    ("total", "page_size", "expected_pages"),
    [(0, 20, 0), (1, 20, 1), (20, 20, 1), (21, 20, 2), (45, 20, 3)],
)
def test_pagination_meta_build_computes_total_pages(
    total: int, page_size: int, expected_pages: int
) -> None:
    meta = PaginationMeta.build(page=1, page_size=page_size, total=total)

    assert meta.total_pages == expected_pages
    assert meta.total == total
