from careerlayer.integrity import BBox


def test_containment_fraction_of_a_box_fully_inside_another() -> None:
    inner = BBox(x0=10, y0=10, x1=20, y1=20)
    outer = BBox(x0=0, y0=0, x1=100, y1=100)

    assert inner.contained_fraction(outer) == 1.0


def test_containment_fraction_of_a_box_half_outside() -> None:
    straddling = BBox(x0=90, y0=0, x1=110, y1=10)
    page = BBox(x0=0, y0=0, x1=100, y1=100)

    assert straddling.contained_fraction(page) == 0.5


def test_containment_fraction_of_a_box_entirely_outside() -> None:
    beyond = BBox(x0=200, y0=200, x1=210, y1=210)
    page = BBox(x0=0, y0=0, x1=100, y1=100)

    assert beyond.contained_fraction(page) == 0.0


def test_union_covers_both_boxes() -> None:
    union = BBox(x0=10, y0=10, x1=20, y1=20).union(BBox(x0=30, y0=5, x1=40, y1=15))

    assert (union.x0, union.y0, union.x1, union.y1) == (10, 5, 40, 20)


def test_a_zero_area_box_does_not_divide_by_zero() -> None:
    empty = BBox(x0=10, y0=10, x1=10, y1=10)

    assert empty.contained_fraction(BBox(x0=0, y0=0, x1=100, y1=100)) == 0.0
