import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 10000))
DEFAULT_HEADER_SIZE = 13267

AUTHOR_NAME = "Your Name"


class TestHandler(BaseHTTPRequestHandler):

    def get_header_size(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        try:
            size = int(params.get("size", [DEFAULT_HEADER_SIZE])[0])
        except ValueError:
            size = DEFAULT_HEADER_SIZE

        return max(1, min(size, 1000000))

    def send_test_headers(self, header_size):
        self.send_response(200)

        self.send_header(
            "Content-Security-Policy",
            "a" * header_size
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.end_headers()

    def do_HEAD(self):
        header_size = self.get_header_size()
        self.send_test_headers(header_size)

    def do_GET(self):
        header_size = self.get_header_size()
        self.send_test_headers(header_size)

        status_class = "success" if header_size <= 65536 else "danger"
        status_text = (
            "Within default configured limit"
            if header_size <= 65536
            else "Exceeds default configured limit"
        )

        html = f"""
        <!DOCTYPE html>
        <html lang="en">

        <head>
            <meta charset="UTF-8">
            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>SearchStax Header Test</title>

            <style>
                * {{
                    box-sizing: border-box;
                }}

                body {{
                    margin: 0;
                    font-family:
                        -apple-system,
                        BlinkMacSystemFont,
                        "Segoe UI",
                        Roboto,
                        Arial,
                        sans-serif;
                    background: #f4f6f8;
                    color: #1f2937;
                }}

                .header {{
                    background: #111827;
                    color: white;
                    padding: 32px 20px;
                }}

                .header-content {{
                    max-width: 950px;
                    margin: auto;
                }}

                .header h1 {{
                    margin: 0 0 8px;
                    font-size: 30px;
                }}

                .header p {{
                    margin: 4px 0;
                    color: #d1d5db;
                }}

                .container {{
                    max-width: 950px;
                    margin: 30px auto;
                    padding: 0 20px;
                }}

                .card {{
                    background: white;
                    border-radius: 12px;
                    padding: 24px;
                    margin-bottom: 22px;
                    box-shadow:
                        0 4px 12px rgba(0, 0, 0, 0.08);
                }}

                .card h2 {{
                    margin-top: 0;
                    font-size: 21px;
                }}

                .size-box {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 20px;
                    flex-wrap: wrap;
                }}

                .size-value {{
                    font-size: 38px;
                    font-weight: 700;
                    color: #2563eb;
                }}

                .size-label {{
                    font-size: 14px;
                    color: #6b7280;
                    margin-top: 4px;
                }}

                .status {{
                    padding: 9px 14px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                }}

                .status.success {{
                    background: #dcfce7;
                    color: #166534;
                }}

                .status.danger {{
                    background: #fee2e2;
                    color: #991b1b;
                }}

                .test-grid {{
                    display: grid;
                    grid-template-columns:
                        repeat(auto-fit, minmax(180px, 1fr));
                    gap: 12px;
                    margin-top: 20px;
                }}

                .test-button {{
                    display: block;
                    text-decoration: none;
                    padding: 16px;
                    border-radius: 9px;
                    text-align: center;
                    font-weight: 600;
                    transition:
                        transform 0.15s ease,
                        box-shadow 0.15s ease;
                }}

                .test-button:hover {{
                    transform: translateY(-2px);
                    box-shadow:
                        0 4px 10px rgba(0, 0, 0, 0.12);
                }}

                .safe {{
                    background: #e0f2fe;
                    color: #075985;
                }}

                .warning {{
                    background: #fef3c7;
                    color: #92400e;
                }}

                .critical {{
                    background: #fee2e2;
                    color: #991b1b;
                }}

                .highlight {{
                    border: 2px solid #2563eb;
                }}

                .info-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }}

                .info-table th,
                .info-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #e5e7eb;
                    text-align: left;
                }}

                .info-table th {{
                    background: #f9fafb;
                }}

                code {{
                    background: #f3f4f6;
                    padding: 3px 7px;
                    border-radius: 5px;
                    font-family: monospace;
                }}

                .note {{
                    background: #eff6ff;
                    border-left: 4px solid #2563eb;
                    padding: 14px 16px;
                    margin-top: 18px;
                    border-radius: 6px;
                }}

                footer {{
                    text-align: center;
                    padding: 30px;
                    color: #6b7280;
                    font-size: 14px;
                }}

                footer strong {{
                    color: #374151;
                }}

                @media (max-width: 600px) {{
                    .header h1 {{
                        font-size: 24px;
                    }}

                    .size-value {{
                        font-size: 30px;
                    }}
                }}
            </style>
        </head>

        <body>

            <div class="header">
                <div class="header-content">
                    <h1>SearchStax Crawler Header Test</h1>
                    <p>QA utility for STUDIO-5693</p>
                    <p>
                        Test configurable HTTP response-header limits
                        during crawler URL validation.
                    </p>
                </div>
            </div>

            <main class="container">

                <section class="card">

                    <h2>Current Test</h2>

                    <div class="size-box">

                        <div>
                            <div class="size-value">
                                {header_size:,}
                            </div>

                            <div class="size-label">
                                Content-Security-Policy header size
                                in bytes
                            </div>
                        </div>

                        <div class="status {status_class}">
                            {status_text}
                        </div>

                    </div>

                    <div class="note">
                        This page sends one deliberately large
                        <code>Content-Security-Policy</code>
                        response header.
                    </div>

                </section>


                <section class="card">

                    <h2>Header Size Tests</h2>

                    <p>
                        Select a test value below. The page reloads
                        with a response header of that approximate size.
                    </p>

                    <div class="test-grid">

                        <a
                            class="test-button safe"
                            href="/?size=5000"
                        >
                            5,000 bytes
                        </a>

                        <a
                            class="test-button safe"
                            href="/?size=8000"
                        >
                            8,000 bytes
                        </a>

                        <a
                            class="test-button warning"
                            href="/?size=8190"
                        >
                            8,190 bytes
                        </a>

                        <a
                            class="test-button warning"
                            href="/?size=8200"
                        >
                            8,200 bytes
                        </a>

                        <a
                            class="test-button warning"
                            href="/?size=10000"
                        >
                            10,000 bytes
                        </a>

                        <a
                            class="test-button warning highlight"
                            href="/?size=13267"
                        >
                            13,267 bytes
                            <br>
                            BHF-like
                        </a>

                        <a
                            class="test-button warning"
                            href="/?size=65535"
                        >
                            65,535 bytes
                        </a>

                        <a
                            class="test-button warning highlight"
                            href="/?size=65536"
                        >
                            65,536 bytes
                            <br>
                            Default limit
                        </a>

                        <a
                            class="test-button critical"
                            href="/?size=65537"
                        >
                            65,537 bytes
                        </a>

                        <a
                            class="test-button critical"
                            href="/?size=70000"
                        >
                            70,000 bytes
                        </a>

                    </div>

                </section>


                <section class="card">

                    <h2>Expected QA Behaviour</h2>

                    <table class="info-table">

                        <thead>
                            <tr>
                                <th>
                                    Manager Configuration
                                </th>

                                <th>
                                    Test Header
                                </th>

                                <th>
                                    Expected Result
                                </th>
                            </tr>
                        </thead>

                        <tbody>

                            <tr>
                                <td>
                                    <code>65536</code>
                                </td>

                                <td>
                                    13,267 bytes
                                </td>

                                <td>
                                    Crawl should start
                                </td>
                            </tr>

                            <tr>
                                <td>
                                    <code>10000</code>
                                </td>

                                <td>
                                    13,267 bytes
                                </td>

                                <td>
                                    Job should become FAILED
                                </td>
                            </tr>

                            <tr>
                                <td>
                                    <code>65536</code>
                                </td>

                                <td>
                                    65,537 bytes
                                </td>

                                <td>
                                    Validation should fail gracefully
                                </td>
                            </tr>

                        </tbody>

                    </table>

                </section>


                <section class="card">

                    <h2>Environment Variable</h2>

                    <p>
                        Default Manager configuration:
                    </p>

                    <code>
                        URL_VALIDATION_MAX_FIELD_SIZE=65536
                    </code>

                    <div class="note">
                        After changing this value, restart the
                        Manager before running the crawler again.
                    </div>

                </section>

            </main>

            <footer>
                Created by <strong>Shubham Sharma</strong>
                <br>
                SearchStax Crawler QA Test Site for Headers Testing 
            </footer>

        </body>

        </html>
        """

        self.wfile.write(html.encode("utf-8"))


if __name__ == "__main__":
    print(f"Starting test server on {HOST}:{PORT}")

    HTTPServer(
        (HOST, PORT),
        TestHandler
    ).serve_forever()
