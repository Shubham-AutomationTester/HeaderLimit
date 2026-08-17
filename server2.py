import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, urlencode

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 10000))

DEFAULT_HEADER_SIZE = 13267
DEFAULT_MANAGER_LIMIT = 65536

AUTHOR_NAME = "Your Name"

HEADER_NAME = "Content-Security-Policy"


class TestHandler(BaseHTTPRequestHandler):

    def get_parameters(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        try:
            header_size = int(
                params.get("size", [DEFAULT_HEADER_SIZE])[0]
            )
        except ValueError:
            header_size = DEFAULT_HEADER_SIZE

        try:
            manager_limit = int(
                params.get("limit", [DEFAULT_MANAGER_LIMIT])[0]
            )
        except ValueError:
            manager_limit = DEFAULT_MANAGER_LIMIT

        # Keep the test endpoint within a reasonable range.
        header_size = max(1, min(header_size, 1000000))
        manager_limit = max(1, min(manager_limit, 1000000))

        return header_size, manager_limit

    def create_header_value(self, requested_size):
        """
        Creates a Content-Security-Policy value with exactly
        requested_size UTF-8 bytes.

        ASCII characters are used, so:
            1 character = 1 byte
        """

        prefix = "default-src 'self'; test-padding "

        if requested_size <= len(prefix):
            return "a" * requested_size

        padding_size = requested_size - len(prefix)

        return prefix + ("a" * padding_size)

    def calculate_header_stats(self, value):
        header_name_bytes = len(
            HEADER_NAME.encode("utf-8")
        )

        header_value_bytes = len(
            value.encode("utf-8")
        )

        separator_bytes = 2       # ": "
        line_ending_bytes = 2     # CRLF

        # Approximate serialized HTTP header line:
        #
        # Content-Security-Policy: <value>\r\n
        #
        wire_size = (
            header_name_bytes
            + separator_bytes
            + header_value_bytes
            + line_ending_bytes
        )

        return {
            "name_bytes": header_name_bytes,
            "value_bytes": header_value_bytes,
            "separator_bytes": separator_bytes,
            "line_ending_bytes": line_ending_bytes,
            "wire_size": wire_size,
        }

    def send_test_headers(self, header_value):
        self.send_response(200)

        self.send_header(
            HEADER_NAME,
            header_value
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

    def do_HEAD(self):
        header_size, _ = self.get_parameters()

        value = self.create_header_value(
            header_size
        )

        self.send_test_headers(value)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self.handle_health()
            return

        if parsed.path == "/api/header-info":
            self.handle_api()
            return

        self.handle_dashboard()

    def handle_health(self):
        body = b"OK"

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)

    def handle_api(self):
        header_size, manager_limit = self.get_parameters()

        value = self.create_header_value(
            header_size
        )

        stats = self.calculate_header_stats(
            value
        )

        result = {
            "ticket": "STUDIO-5693",
            "header_name": HEADER_NAME,
            "requested_value_bytes": header_size,
            "actual_value_bytes": stats["value_bytes"],
            "header_name_bytes": stats["name_bytes"],
            "separator_bytes": stats["separator_bytes"],
            "line_ending_bytes": stats["line_ending_bytes"],
            "approx_wire_field_bytes": stats["wire_size"],
            "manager_limit": manager_limit,
            "value_exceeds_manager_limit":
                stats["value_bytes"] > manager_limit,
        }

        body = json.dumps(
            result,
            indent=2
        ).encode("utf-8")

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)

    def handle_dashboard(self):
        header_size, manager_limit = self.get_parameters()

        header_value = self.create_header_value(
            header_size
        )

        stats = self.calculate_header_stats(
            header_value
        )

        value_passes = (
            stats["value_bytes"] <= manager_limit
        )

        status_text = (
            "EXPECTED TO PASS"
            if value_passes
            else "EXPECTED TO FAIL"
        )

        status_class = (
            "success"
            if value_passes
            else "failure"
        )

        old_aiohttp_passes = (
            stats["value_bytes"] <= 8190
        )

        aiohttp_status = (
            "PASS"
            if old_aiohttp_passes
            else "FAIL"
        )

        aiohttp_class = (
            "success-text"
            if old_aiohttp_passes
            else "failure-text"
        )

        presets = [
            (5000, "Small header"),
            (8000, "Below aiohttp default"),
            (8190, "aiohttp default boundary"),
            (8191, "Above aiohttp default"),
            (10000, "Negative QA test"),
            (13267, "BHF-like header"),
            (65535, "Below new default"),
            (65536, "New configured default"),
            (65537, "Above new default"),
            (70000, "Large failure test"),
        ]

        preset_html = ""

        for size, description in presets:
            query = urlencode({
                "size": size,
                "limit": manager_limit
            })

            preset_html += f"""
            <a class="preset" href="/?{query}">
                <span class="preset-size">
                    {size:,} bytes
                </span>

                <span class="preset-description">
                    {description}
                </span>
            </a>
            """

        # Only show a small preview instead of printing
        # thousands of characters on the page.
        preview_length = min(
            len(header_value),
            120
        )

        header_preview = (
            header_value[:preview_length]
            + (
                "..."
                if len(header_value) > preview_length
                else ""
            )
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

<title>
    SearchStax Header Validation Test
</title>

<style>

    * {{
        box-sizing: border-box;
    }}

    body {{
        margin: 0;
        background: #f5f7fb;
        color: #182230;
        font-family:
            Inter,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Arial,
            sans-serif;
    }}

    .page {{
        max-width: 1100px;
        margin: auto;
        padding: 40px 24px 60px;
    }}

    .hero {{
        background: #ffffff;
        border: 1px solid #e5e9f0;
        border-radius: 18px;
        padding: 32px;
        margin-bottom: 24px;
    }}

    .ticket {{
        display: inline-block;
        background: #eef4ff;
        color: #2659a8;
        border-radius: 999px;
        padding: 7px 12px;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 12px;
    }}

    h1 {{
        margin: 0 0 10px;
        font-size: 31px;
    }}

    h2 {{
        margin-top: 0;
    }}

    .subtitle {{
        color: #5f6c7b;
        line-height: 1.6;
        max-width: 850px;
    }}

    .status {{
        margin-top: 25px;
        padding: 18px;
        border-radius: 12px;
        font-weight: 700;
    }}

    .status.success {{
        background: #eaf8ef;
        border: 1px solid #aadbb9;
        color: #166534;
    }}

    .status.failure {{
        background: #fff0f0;
        border: 1px solid #efb1b1;
        color: #b42318;
    }}

    .grid {{
        display: grid;
        grid-template-columns:
            repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin: 24px 0;
    }}

    .card {{
        background: white;
        border: 1px solid #e5e9f0;
        border-radius: 14px;
        padding: 20px;
    }}

    .label {{
        color: #667085;
        font-size: 13px;
        margin-bottom: 8px;
    }}

    .value {{
        font-size: 26px;
        font-weight: 700;
    }}

    .unit {{
        font-size: 13px;
        color: #667085;
        margin-top: 5px;
    }}

    .section {{
        background: white;
        border: 1px solid #e5e9f0;
        border-radius: 18px;
        padding: 28px;
        margin-top: 24px;
    }}

    .calculation {{
        background: #101828;
        color: #e6edf6;
        padding: 22px;
        border-radius: 12px;
        font-family:
            "SFMono-Regular",
            Consolas,
            monospace;
        overflow-wrap: anywhere;
        line-height: 1.8;
    }}

    .highlight {{
        color: #7dd3fc;
    }}

    .success-text {{
        color: #16803a;
        font-weight: 700;
    }}

    .failure-text {{
        color: #c62828;
        font-weight: 700;
    }}

    .test-form {{
        display: grid;
        grid-template-columns:
            repeat(auto-fit, minmax(220px, 1fr));
        gap: 15px;
        align-items: end;
    }}

    label {{
        display: block;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 7px;
    }}

    input {{
        width: 100%;
        border: 1px solid #cfd7e3;
        border-radius: 9px;
        padding: 12px;
        font-size: 15px;
    }}

    button {{
        width: 100%;
        background: #2557d6;
        color: white;
        border: 0;
        border-radius: 9px;
        padding: 13px;
        font-weight: 600;
        cursor: pointer;
    }}

    .presets {{
        display: grid;
        grid-template-columns:
            repeat(auto-fit, minmax(210px, 1fr));
        gap: 10px;
    }}

    .preset {{
        text-decoration: none;
        border: 1px solid #e1e6ed;
        border-radius: 10px;
        padding: 13px;
        color: inherit;
        transition: 0.15s;
    }}

    .preset:hover {{
        border-color: #2557d6;
        background: #f5f8ff;
    }}

    .preset-size {{
        display: block;
        font-weight: 700;
        margin-bottom: 3px;
    }}

    .preset-description {{
        color: #667085;
        font-size: 12px;
    }}

    .preview {{
        background: #f7f8fa;
        border: 1px solid #e2e6ec;
        border-radius: 10px;
        padding: 16px;
        word-break: break-all;
        font-family: monospace;
        font-size: 13px;
        line-height: 1.6;
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
    }}

    th,
    td {{
        text-align: left;
        padding: 13px;
        border-bottom: 1px solid #e8ebef;
    }}

    th {{
        color: #667085;
        font-size: 13px;
    }}

    .note {{
        background: #fffbea;
        border: 1px solid #f4dfa0;
        padding: 17px;
        border-radius: 10px;
        margin-top: 18px;
        line-height: 1.55;
    }}

    footer {{
        margin-top: 32px;
        text-align: center;
        color: #778293;
        font-size: 13px;
    }}

</style>

</head>

<body>

<div class="page">

    <section class="hero">

        <span class="ticket">
            STUDIO-5693
        </span>

        <h1>
            SearchStax Crawler Header Validation Lab
        </h1>

        <p class="subtitle">
            This test site generates a configurable
            <strong>Content-Security-Policy</strong>
            response header. It can be used to verify
            URL_VALIDATION_MAX_FIELD_SIZE behavior in
            SearchStax Crawler Manager.
        </p>

        <div class="status {status_class}">
            {status_text}

            &nbsp;—&nbsp;

            Header value:
            {stats["value_bytes"]:,} bytes

            &nbsp;|&nbsp;

            Configured test limit:
            {manager_limit:,} bytes
        </div>

    </section>


    <div class="grid">

        <div class="card">
            <div class="label">
                Header Value
            </div>

            <div class="value">
                {stats["value_bytes"]:,}
            </div>

            <div class="unit">
                bytes
            </div>
        </div>


        <div class="card">
            <div class="label">
                Header Name
            </div>

            <div class="value">
                {stats["name_bytes"]}
            </div>

            <div class="unit">
                bytes
            </div>
        </div>


        <div class="card">
            <div class="label">
                Approx. HTTP Field
            </div>

            <div class="value">
                {stats["wire_size"]:,}
            </div>

            <div class="unit">
                bytes on the wire
            </div>
        </div>


        <div class="card">
            <div class="label">
                Test Manager Limit
            </div>

            <div class="value">
                {manager_limit:,}
            </div>

            <div class="unit">
                bytes
            </div>
        </div>

    </div>


    <section class="section">

        <h2>
            Test a Header Size
        </h2>

        <form
            class="test-form"
            method="GET"
            action="/"
        >

            <div>
                <label for="size">
                    Header value size
                </label>

                <input
                    id="size"
                    name="size"
                    type="number"
                    min="1"
                    max="1000000"
                    value="{header_size}"
                >
            </div>


            <div>
                <label for="limit">
                    Manager max field size
                </label>

                <input
                    id="limit"
                    name="limit"
                    type="number"
                    min="1"
                    max="1000000"
                    value="{manager_limit}"
                >
            </div>


            <div>
                <button type="submit">
                    Generate Test
                </button>
            </div>

        </form>

        <div class="note">
            The <strong>limit</strong> parameter above is
            only used by this page to show the expected
            result. The real crawler limit must still be
            configured in Manager using
            <strong>URL_VALIDATION_MAX_FIELD_SIZE</strong>.
        </div>

    </section>


    <section class="section">

        <h2>
            Header Size Calculation
        </h2>

        <p>
            The HTTP response contains a field similar to:
        </p>

        <div class="calculation">

            Content-Security-Policy: &lt;generated value&gt;\\r\\n

            <br><br>

            Header name
            =
            <span class="highlight">
                {stats["name_bytes"]} bytes
            </span>

            <br>

            ": "
            =
            <span class="highlight">
                {stats["separator_bytes"]} bytes
            </span>

            <br>

            Header value
            =
            <span class="highlight">
                {stats["value_bytes"]:,} bytes
            </span>

            <br>

            CRLF
            =
            <span class="highlight">
                {stats["line_ending_bytes"]} bytes
            </span>

            <br><br>

            Approximate serialized field size

            =
            {stats["name_bytes"]}
            +
            {stats["separator_bytes"]}
            +
            {stats["value_bytes"]}
            +
            {stats["line_ending_bytes"]}

            =
            <span class="highlight">
                {stats["wire_size"]:,} bytes
            </span>

        </div>

        <div class="note">
            For STUDIO-5693, the important configurable
            value is aiohttp's maximum HTTP header field
            size. This dashboard separately displays the
            generated header <strong>value size</strong>
            and the approximate complete serialized HTTP
            field size so the difference is visible.
        </div>

    </section>


    <section class="section">

        <h2>
            aiohttp Comparison
        </h2>

        <table>

            <thead>
                <tr>
                    <th>
                        Configuration
                    </th>

                    <th>
                        Limit
                    </th>

                    <th>
                        Current Test
                    </th>
                </tr>
            </thead>

            <tbody>

                <tr>
                    <td>
                        Original aiohttp default
                    </td>

                    <td>
                        8,190 bytes
                    </td>

                    <td class="{aiohttp_class}">
                        {aiohttp_status}
                    </td>
                </tr>


                <tr>
                    <td>
                        STUDIO-5693 default
                    </td>

                    <td>
                        65,536 bytes
                    </td>

                    <td class="{
                        "success-text"
                        if stats["value_bytes"] <= 65536
                        else "failure-text"
                    }">

                        {
                            "PASS"
                            if stats["value_bytes"] <= 65536
                            else "FAIL"
                        }

                    </td>
                </tr>


                <tr>
                    <td>
                        Current displayed test limit
                    </td>

                    <td>
                        {manager_limit:,} bytes
                    </td>

                    <td class="{
                        "success-text"
                        if value_passes
                        else "failure-text"
                    }">

                        {
                            "PASS"
                            if value_passes
                            else "FAIL"
                        }

                    </td>
                </tr>

            </tbody>

        </table>

    </section>


    <section class="section">

        <h2>
            Quick QA Presets
        </h2>

        <div class="presets">
            {preset_html}
        </div>

    </section>


    <section class="section">

        <h2>
            Current Header Preview
        </h2>

        <p>
            The complete header value contains
            <strong>{stats["value_bytes"]:,} bytes</strong>.
            Only the first {preview_length} characters are
            displayed below.
        </p>

        <div class="preview">
            {HEADER_NAME}: {header_preview}
        </div>

    </section>


    <section class="section">

        <h2>
            QA Output
        </h2>

        <table>

            <tbody>

                <tr>
                    <th>
                        Header
                    </th>

                    <td>
                        {HEADER_NAME}
                    </td>
                </tr>


                <tr>
                    <th>
                        Requested value
                    </th>

                    <td>
                        {header_size:,} bytes
                    </td>
                </tr>


                <tr>
                    <th>
                        Actual generated value
                    </th>

                    <td>
                        {stats["value_bytes"]:,} bytes
                    </td>
                </tr>


                <tr>
                    <th>
                        Approximate complete field
                    </th>

                    <td>
                        {stats["wire_size"]:,} bytes
                    </td>
                </tr>


                <tr>
                    <th>
                        Manager test limit
                    </th>

                    <td>
                        {manager_limit:,} bytes
                    </td>
                </tr>


                <tr>
                    <th>
                        Expected result
                    </th>

                    <td class="{
                        "success-text"
                        if value_passes
                        else "failure-text"
                    }">

                        {status_text}

                    </td>
                </tr>

            </tbody>

        </table>


        <p style="margin-top: 20px;">
            JSON diagnostic endpoint:
            <a href="/api/header-info?size={header_size}&limit={manager_limit}">
                /api/header-info
            </a>
        </p>

        <p>
            Health endpoint:
            <a href="/health">
                /health
            </a>
        </p>

    </section>


    <footer>
        Created by <strong>{AUTHOR_NAME}</strong>
        &nbsp;•&nbsp;
        SearchStax Crawler QA
        &nbsp;•&nbsp;
        STUDIO-5693
    </footer>

</div>

</body>

</html>
"""

        body = html.encode("utf-8")

        # Send the actual large response header.
        self.send_response(200)

        self.send_header(
            HEADER_NAME,
            header_value
        )

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)

    def log_message(self, format, *args):
        print(
            f"{self.client_address[0]} "
            f"- {format % args}"
        )


if __name__ == "__main__":

    print()
    print("==========================================")
    print(" SearchStax Header Validation Test Server")
    print("==========================================")
    print()
    print(f"Host:   {HOST}")
    print(f"Port:   {PORT}")
    print(f"Author: {AUTHOR_NAME}")
    print()
    print(
        f"Default header size: "
        f"{DEFAULT_HEADER_SIZE:,} bytes"
    )
    print()

    server = HTTPServer(
        (HOST, PORT),
        TestHandler
    )

    server.serve_forever()
