document.addEventListener('DOMContentLoaded', async () => {
    // 1. Fetch Data
    let dashboardData;
    try {
        const response = await fetch('../data/ga_data.json');
        if (!response.ok) throw new Error('Data file not found');
        dashboardData = await response.json();
    } catch (error) {
        console.warn('Failed to load JSON data. Using fallback dummy data for preview.', error);
        // Fallback for immediate UI preview without running the python script
        dashboardData = {
            "last_updated": new Date().toISOString(),
            "ab_test": {
                "A": { "views": 1500, "scroll_75": 450, "clicks": 180, "avg_session_duration": 120 },
                "B": { "views": 1450, "scroll_75": 600, "clicks": 290, "avg_session_duration": 150 }
            },
            "channels": [
                { "source": "m.facebook.com / referral", "users": 800 },
                { "source": "instagram.com / referral", "users": 650 },
                { "source": "google / organic", "users": 300 },
                { "source": "(direct) / (none)", "users": 200 }
            ]
        };
    }

    // 2. Update Header & Summary Metrics
    const lastUpdatedDate = new Date(dashboardData.last_updated);
    document.getElementById('last-updated').textContent = `Last Updated: ${lastUpdatedDate.toLocaleString()}`;

    const groupA = dashboardData.ab_test.A;
    const groupB = dashboardData.ab_test.B;

    const totalViews = groupA.views + groupB.views;
    const totalClicks = groupA.clicks + groupB.clicks;
    const convRate = totalViews > 0 ? ((totalClicks / totalViews) * 100).toFixed(1) : 0;

    document.getElementById('total-views').textContent = totalViews.toLocaleString();
    document.getElementById('total-clicks').textContent = totalClicks.toLocaleString();
    document.getElementById('overall-conversion').textContent = `${convRate}%`;

    // 3. Render Charts
    renderFunnelChart(groupA, groupB);
    renderChannelChart(dashboardData.channels);
});

function renderFunnelChart(groupA, groupB) {
    const ctx = document.getElementById('funnelChart').getContext('2d');

    // Calculate relative percentages for better visualization
    // Step 1 is always 100%. Step 2 is % of views. Step 3 is % of views.
    const funnelSteps = ['1. Page View', '2. Scroll (Engagement Proxy)', '3. CTA Click (Apply)'];

    // Raw numbers are more important for comparison, so we show absolute values
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: funnelSteps,
            datasets: [
                {
                    label: 'Group A (작은 실패)',
                    data: [groupA.views, groupA.scroll_75, groupA.clicks],
                    backgroundColor: 'rgba(0, 201, 161, 0.8)',
                    borderColor: 'rgba(0, 201, 161, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Group B (안전한 도전)',
                    data: [groupB.views, groupB.scroll_75, groupB.clicks],
                    backgroundColor: 'rgba(255, 51, 102, 0.8)',
                    borderColor: 'rgba(255, 51, 102, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#ffffff' }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.dataset.label || '';
                            if (label) { label += ': '; }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y;
                                // Calculate conversion drop-off on tooltip
                                if (context.dataIndex > 0) {
                                    const initialViews = context.dataset.data[0];
                                    const rate = ((context.parsed.y / initialViews) * 100).toFixed(1);
                                    label += ` (${rate}% of initial)`;
                                }
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#a0a0ab' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#a0a0ab' }
                }
            }
        }
    });
}

function renderChannelChart(channelsData) {
    const ctx = document.getElementById('channelChart').getContext('2d');

    // Sort and take top 5
    const topChannels = [...channelsData]
        .sort((a, b) => b.users - a.users)
        .slice(0, 5);

    const labels = topChannels.map(c => c.source);
    const data = topChannels.map(c => c.users);

    // Brand colors generator
    const backgroundColors = [
        '#00C9A1', '#33E0C1', '#009F81', '#1A7A66', '#0A4A3D'
    ];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#a0a0ab', font: { size: 12 } }
                }
            },
            cutout: '60%'
        }
    });
}
