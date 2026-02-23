import os
import json
from datetime import datetime
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    FilterExpressionList,
    Metric,
    RunReportRequest,
)

# acts29_gen2.html 페이지 경로 (pagePath 필터용)
TARGET_PAGE = "/groute-contact/acts29_gen2.html"


def fetch_ga4_data():
    property_id = os.environ.get("GA_PROPERTY_ID")
    if not property_id:
        raise RuntimeError("GA_PROPERTY_ID environment variable not found.")

    client = BetaAnalyticsDataClient()

    # 공통 필터: pagePath + eventName
    page_and_event_filter = FilterExpression(
        and_group=FilterExpressionList(
            expressions=[
                FilterExpression(
                    filter=Filter(
                        field_name="pagePath",
                        string_filter=Filter.StringFilter(
                            value=TARGET_PAGE,
                            match_type=Filter.StringFilter.MatchType.CONTAINS,
                        ),
                    )
                ),
                FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        in_list_filter=Filter.InListFilter(
                            values=["detail_page_view", "scroll_depth", "time_on_page", "cta_click"]
                        ),
                    )
                ),
            ]
        )
    )

    # 1. 이벤트 + A/B 그룹별 메트릭
    # NOTE: customEvent:ab_group 사용하려면 GA4 Admin에서 커스텀 차원 등록 필요
    request_events = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="eventName"),
            Dimension(name="customEvent:ab_group"),
        ],
        metrics=[
            Metric(name="eventCount"),
            Metric(name="totalUsers"),
        ],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimension_filter=page_and_event_filter,
    )

    # 2. 스크롤 심도별 데이터 (scroll_percent 커스텀 차원)
    scroll_filter = FilterExpression(
        and_group=FilterExpressionList(
            expressions=[
                FilterExpression(
                    filter=Filter(
                        field_name="pagePath",
                        string_filter=Filter.StringFilter(
                            value=TARGET_PAGE,
                            match_type=Filter.StringFilter.MatchType.CONTAINS,
                        ),
                    )
                ),
                FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(
                            value="scroll_depth",
                            match_type=Filter.StringFilter.MatchType.EXACT,
                        ),
                    )
                ),
            ]
        )
    )

    request_scroll = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="customEvent:ab_group"),
            Dimension(name="customEvent:scroll_percent"),
        ],
        metrics=[Metric(name="eventCount")],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimension_filter=scroll_filter,
    )

    # 3. 유입 채널 (acts29_gen2 페이지 한정)
    page_filter = FilterExpression(
        filter=Filter(
            field_name="pagePath",
            string_filter=Filter.StringFilter(
                value=TARGET_PAGE,
                match_type=Filter.StringFilter.MatchType.CONTAINS,
            ),
        )
    )

    request_channels = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name="sessionSourceMedium")],
        metrics=[
            Metric(name="totalUsers"),
            Metric(name="screenPageViews"),
        ],
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimension_filter=page_filter,
    )

    # API 호출
    response_events = client.run_report(request_events)
    response_scroll = client.run_report(request_scroll)
    response_channels = client.run_report(request_channels)

    # 결과 파싱
    data = {
        "last_updated": datetime.now().isoformat(),
        "ab_test": {
            "A": {
                "views": 0,
                "scroll_25": 0, "scroll_50": 0, "scroll_75": 0, "scroll_100": 0,
                "clicks": 0,
                "time_events": 0, "total_time": 0,
            },
            "B": {
                "views": 0,
                "scroll_25": 0, "scroll_50": 0, "scroll_75": 0, "scroll_100": 0,
                "clicks": 0,
                "time_events": 0, "total_time": 0,
            },
        },
        "channels": [],
    }

    # 이벤트 데이터 처리
    for row in response_events.rows:
        event_name = row.dimension_values[0].value
        ab_group = row.dimension_values[1].value
        count = int(row.metric_values[0].value)

        if ab_group not in ("A", "B"):
            continue

        if event_name == "detail_page_view":
            data["ab_test"][ab_group]["views"] += count
        elif event_name == "cta_click":
            data["ab_test"][ab_group]["clicks"] += count
        elif event_name == "time_on_page":
            data["ab_test"][ab_group]["time_events"] += count

    # 스크롤 심도 데이터 처리
    for row in response_scroll.rows:
        ab_group = row.dimension_values[0].value
        scroll_pct = row.dimension_values[1].value  # "25", "50", "75", "100"
        count = int(row.metric_values[0].value)

        if ab_group not in ("A", "B"):
            continue

        key = f"scroll_{scroll_pct}"
        if key in data["ab_test"][ab_group]:
            data["ab_test"][ab_group][key] += count

    # 채널 데이터 처리
    for row in response_channels.rows:
        source_medium = row.dimension_values[0].value
        users = int(row.metric_values[0].value)
        data["channels"].append({"source": source_medium, "users": users})

    return data


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    report_data = fetch_ga4_data()

    with open("data/ga_data.json", "w") as f:
        json.dump(report_data, f, indent=4)
    print("Data successfully exported to data/ga_data.json")
