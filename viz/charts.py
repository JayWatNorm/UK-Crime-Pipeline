"""Plotly figure builders.

Each function takes a DataFrame and returns a Plotly figure. No database
access here on purpose -- keeping the charts free of I/O means they can be
tested with a handful of hand-made rows, and build_report.py stays the only
place that knows about connections.
"""
import plotly.express as px

# Pinning the colour range stops a handful of extreme areas dominating the
# scale. Without it, one LSOA at +900% would compress every normal area
# into indistinguishable neutral. Values beyond the range still render --
# they just clamp to the end colour rather than stretching the palette.
COLOUR_RANGE = (-1.0, 1.0)

# Diverging blue<->red rather than red/green: around 8% of men have some
# form of red-green colour blindness, which makes it the worst possible
# pairing for a continuous scale like this. _r reverses the scale so blue
# reads as a fall and red as a rise.
COLOUR_SCALE = "RdBu_r"


def build_change_map(map_data, height=760):
    """Map of year-over-year change in recorded crime, one marker per LSOA.

    Rendered as large semi-transparent markers rather than a density
    heatmap: density layers accumulate, so adjacent areas of +50 and -50
    would cancel to neutral and dense clusters of small changes would light
    up as though they were large ones. Markers keep each area's own signed
    value while still blending into a heatmap-like surface at national zoom.
    """
    fig = px.scatter_map(
        map_data,
        lat="latitude",
        lon="longitude",
        color="crime_change_pct",
        color_continuous_scale=COLOUR_SCALE,
        color_continuous_midpoint=0,
        range_color=COLOUR_RANGE,
        hover_name="lsoa_code",
        # Absolute counts alongside the percentage, so a reader can tell a
        # genuine trend from a one-off event inflating last year's baseline.
        hover_data={
            "cy_crimes": True,
            "ly_crimes": True,
            "crime_change": True,
            "crime_change_pct": ":.1%",
            "latitude": False,
            "longitude": False,
        },
        map_style="open-street-map",
        zoom=5.2,
        center={"lat": 52.8, "lon": -2.0},
        height=height,
        labels={
            "crime_change_pct": "Change",
            "cy_crimes": "This period",
            "ly_crimes": "Same period last year",
            "crime_change": "Difference",
        },
    )

    fig.update_traces(marker={"size": 33, "opacity": 0.75})

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar={
            "title": "Change",
            # Labelling the ends as "or more" is more honest than implying
            # the scale stops there, given values beyond it are clamped.
            "tickvals": [-1.0, -0.5, 0.0, 0.5, 1.0],
            "ticktext": ["-100% or more", "-50%", "No change", "+50%", "+100% or more"],
        },
    )

    return fig


def build_coverage_pie(coverage_data, height=280):
    """Three-way split of how crimes are (or aren't) mappable.

    Deliberately three slices rather than two: Northern Ireland having no
    LSOA code is a structural geography difference, not a data quality
    problem, and lumping it in with genuinely missing codes would present
    the two as the same kind of gap.

    Expects columns: category, crimes.
    """
    fig = px.pie(
        coverage_data,
        names="category",
        values="crimes",
        hole=0.45,
        color="category",
        color_discrete_map={
            "Mapped": "#4C78A8",
            "Northern Ireland (no LSOA geography)": "#B79A6E",
            "Missing LSOA code": "#C4C7CC",
        },
        height=height,
    )

    fig.update_traces(textposition="inside", textinfo="percent")
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend={"orientation": "h", "y": -0.1, "font": {"size": 11}},
    )

    return fig


def figure_to_html(fig):
    """Render a figure as an HTML fragment for embedding in the template.

    include_plotlyjs=False because the template loads Plotly once from CDN;
    bundling it per figure would multiply the file size for no benefit.
    """
    return fig.to_html(full_html=False, include_plotlyjs=False)
