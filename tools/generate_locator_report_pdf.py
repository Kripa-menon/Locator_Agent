from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    PageBreak,
    Table,
    ListFlowable,
    ListItem,
    Flowable,
)


class WorkflowDiagram(Flowable):
    def __init__(self, steps, box_width=140, box_height=58, gap=26, row_gap=22):
        self.steps = steps
        self.box_width = box_width
        self.box_height = box_height
        self.gap = gap
        self.row_gap = row_gap
        self.colors = [
            colors.HexColor('#EAF2FF'),
            colors.HexColor('#EAFBF3'),
            colors.HexColor('#FFF3D9'),
            colors.HexColor('#FDEAE8'),
            colors.HexColor('#F1EAFD'),
            colors.HexColor('#E8F9FF'),
            colors.HexColor('#EEF7E8'),
        ]

    def wrap(self, availWidth, availHeight):
        return (availWidth, 180)

    def draw(self):
        canvas = self.canv
        total_width = len(self.steps) * self.box_width + (len(self.steps) - 1) * self.gap
        start_x = 50
        y = 690
        for idx, step in enumerate(self.steps):
            x = start_x + idx * (self.box_width + self.gap)
            fill_color = self.colors[idx % len(self.colors)]
            canvas.setFillColor(fill_color)
            canvas.setStrokeColor(colors.black)
            canvas.roundRect(x, y, self.box_width, self.box_height, 10, stroke=1, fill=1)
            canvas.setFillColor(colors.black)
            canvas.setFont('Helvetica-Bold', 7)
            lines = step.split('\n')
            text_y = y + (self.box_height / 2) + (len(lines) - 1) * 5
            for line in lines:
                canvas.drawCentredString(x + self.box_width / 2, text_y, line)
                text_y -= 12
            if idx < len(self.steps) - 1:
                arrow_x1 = x + self.box_width
                arrow_x2 = x + self.box_width + self.gap / 2
                canvas.setStrokeColor(colors.black)
                canvas.setFillColor(colors.black)
                canvas.line(arrow_x1, y + self.box_height / 2, arrow_x2, y + self.box_height / 2)
                canvas.line(arrow_x2 - 8, y + self.box_height / 2 - 6, arrow_x2, y + self.box_height / 2)
                canvas.line(arrow_x2 - 8, y + self.box_height / 2 + 6, arrow_x2, y + self.box_height / 2)


def build_document(output_path: str):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'title',
        parent=styles['Title'],
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=10,
    )
    h1 = ParagraphStyle(
        'h1',
        parent=styles['Heading1'],
        fontSize=14,
        leading=18,
        spaceBefore=10,
        spaceAfter=8,
    )
    h2 = ParagraphStyle(
        'h2',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        spaceBefore=8,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        'body',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    bullet = ParagraphStyle(
        'bullet',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        leftIndent=18,
        bulletIndent=8,
        spaceAfter=4,
    )

    story = []
    story.append(Paragraph('Hexaware-GenAI', title_style))
    story.append(Paragraph('Unlocking Innovation-', title_style))
    story.append(Paragraph('Your Path to AI-Driven Excellence', title_style))
    story.append(PageBreak())

    story.append(Paragraph('Scope Of the project', h1))
    story.append(Paragraph('Project Title : Locator Finder Agent', body))
    story.append(Paragraph('Project Objectives:', h2))
    objectives = [
        'Build a local web application that accepts a page URL and a natural-language element description.',
        'Use Playwright Chromium to open the page in a visible browser and inspect the live DOM.',
        'Identify the best Selenium locator for the target element using structural and attribute-based ranking rules.',
        'Return the best locator, ranked alternatives, match counts, risk flags, and ready-to-use code snippets.',
        'Support login flows by allowing the user to sign in manually in the browser before continuing.',
        'Detect frames, shadow DOM, and cross-origin layout conditions that affect selector reliability.',
        'Generate code in Python, Java, C#, JavaScript, and TypeScript for immediate reuse.',
        'Provide a local-first, session-aware interface that keeps browser state and element matches organized.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, bullet), bulletType='bullet', value='•') for item in objectives],
            bulletType='bullet',
        )
    )
    story.append(Paragraph('Deliverables:', h2))
    deliverables = [
        'Local FastAPI backend with browser session management.',
        'Playwright-powered page inspection and live verification.',
        'DOM locator ranking and verification engine.',
        'Selenium code generator for multiple languages.',
        'Single-page HTML/CSS/JS frontend for interaction and result display.',
        'Test suite covering positive and negative selector scenarios.',
        'README, requirements, and setup instructions.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, bullet), bulletType='bullet', value='•') for item in deliverables],
            bulletType='bullet',
        )
    )
    story.append(PageBreak())

    story.append(Paragraph('Design', h1))
    story.append(Paragraph('Design Diagram:', h2))
    workflow_steps = [
        'User URL + Description',
        'Browser Session\nPlaywright Chromium',
        'Live DOM Inspection\nElement Extraction',
        'Candidate Ranking\nID / Name / TestID /\nXPath / Text / Class',
        'Match Verification\nRisk Detection\nFrame + Shadow Checks',
        'Result Card + Code\nGeneration',
        'User Copy / Highlight\nVerify in Browser',
    ]
    story.append(WorkflowDiagram(workflow_steps))
    story.append(Spacer(1, 20))
    story.append(Paragraph('Design Description:', h2))
    story.append(
        Paragraph(
            'Browser Interface: The application creates a visible local browser instance using Playwright Chromium. Users can open a URL, log in when needed, and continue the session without changing the browser state externally.',
            body,
        )
    )
    story.append(
        Paragraph(
            'Locator Intelligence Module: The core engine inspects rendered DOM elements and extracts attributes such as id, name, data-testid, aria-label, placeholder, and classes. It ranks selectors according to their stability and realism, preferring real semantic attributes over generic text and positional XPath.',
            body,
        )
    )
    story.append(
        Paragraph(
            'Verification and Safety Layer: The system verifies each candidate locator against the live page and reports match counts. It also flags conditions such as auto-generated IDs, ambiguous selectors, iframe usage, and shadow DOM differences so users can judge reliability before coding.',
            body,
        )
    )
    story.append(
        Paragraph(
            'Result and Code Generation Layer: The UI displays the best locator, its match count, risk summary, and ranked alternatives. It also generates ready-to-use Selenium code in multiple programming languages so the user can paste directly into tests.',
            body,
        )
    )
    story.append(
        Paragraph(
            'Session Management: Each browser interaction can be associated with a named session. The app supports creating, activating, refreshing, and closing sessions so users can work across multiple flows without stale page state.',
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph('Design', h1))
    story.append(Paragraph('Workflow', h2))
    workflow = [
        'User enters a target URL in the local app.',
        'The app opens the URL in a visible Chromium browser.',
        'The user logs in manually when the site requires authentication.',
        'The user provides a natural-language description such as “username field” or “submit button”.',
        'The backend inspects the live DOM and collects candidate elements.',
        'The ranking engine prefers stable selectors such as ID, data-testid, and name-based attributes.',
        'Each candidate is validated live to compute match counts and capture risk information.',
        'The best locator is returned alongside alternatives, match counts, and reasoning.',
        'The app creates ready-to-use Selenium snippets in the requested language.',
        'The user can highlight the selected target in the browser or copy the snippet directly.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(step, bullet), bulletType='bullet', value='•') for step in workflow],
            bulletType='bullet',
        )
    )
    story.append(PageBreak())

    story.append(Paragraph('Test Cases', h1))
    story.append(Paragraph('Positive Test Cases', h2))
    positive = [
        'TC #1: Open a valid public page successfully.',
        'TC #2: Enter a clear description such as “login button” and get a valid locator result.',
        'TC #3: Submit a selector through the pick action and verify the match result is calculated.',
        'TC #4: Rank id and data-testid selectors above generic text or class-based alternatives.',
        'TC #5: Confirm the code generation output is valid for Python, Java, C#, JavaScript, and TypeScript.',
        'TC #6: Verify live highlighting selects the proper DOM element.',
        'TC #7: Validate session creation, activation, and closure workflow.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, bullet), bulletType='bullet', value='•') for item in positive],
            bulletType='bullet',
        )
    )
    story.append(Paragraph('Negative Test Cases', h2))
    negative = [
        'TC #8: Empty URL or missing description should return a validation error.',
        'TC #9: Invalid selector input should not produce a false-positive target.',
        'TC #10: Generic page header or nav links should not be ranked above the required form control.',
        'TC #11: Ambiguous selectors with multiple matches should be flagged with low stability.',
        'TC #12: Shadow DOM and iframe elements should be detected and flagged clearly.',
        'TC #13: Cross-origin frames should warn the user instead of pretending the selector is fully reliable.',
        'TC #14: Duplicate selector values should be deduplicated before ranking and display.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, bullet), bulletType='bullet', value='•') for item in negative],
            bulletType='bullet',
        )
    )
    story.append(PageBreak())

    story.append(Paragraph('Tools and Code details', h1))
    story.append(Paragraph('Third party tools Details:', h2))
    tool_table = Table(
        [
            ['Tool', 'Open source / Licensed', 'URL', 'Purpose'],
            ['FastAPI', 'Open source', 'https://fastapi.tiangolo.com', 'Backend API server and local web app'],
            ['Playwright', 'Open source', 'https://playwright.dev', 'Browser automation and DOM inspection'],
            ['Pytest', 'Open source', 'https://pytest.org', 'Automated test execution'],
            ['Python', 'Open source', 'https://www.python.org', 'Core backend language'],
            ['HTML/CSS/JS', 'Open source', 'https://developer.mozilla.org', 'Front-end result rendering and interactions'],
        ],
        colWidths=[90, 120, 120, 170],
    )
    tool_table.setStyle(
        [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf2ff')),
        ]
    )
    story.append(tool_table)
    story.append(Spacer(1, 12))
    story.append(Paragraph('Technologies used to develop in this project', h2))
    tech_table = Table(
        [
            ['Technology name', 'Version / usage', 'Purpose'],
            ['Python', '3.x', 'Application logic, API, and automation'],
            ['FastAPI', 'Modern API framework', 'Local web server for browser and locator services'],
            ['Playwright', 'Chromium automation', 'Live page inspection and DOM interaction'],
            ['HTML / CSS / JavaScript', 'Front-end stack', 'Result card UI and interactivity'],
            ['Pytest', 'Automated validation', 'Regression and feature testing'],
        ],
        colWidths=[120, 140, 200],
    )
    tech_table.setStyle(
        [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf2ff')),
        ]
    )
    story.append(tech_table)
    story.append(PageBreak())

    story.append(Paragraph('Functional Requirements', h1))
    fr = [
        'Accept URL and description from the user.',
        'Open and maintain a local live browser session.',
        'Allow manual authentication when needed.',
        'Analyze DOM elements and rank candidates by stability.',
        'Return best locator plus ranked alternatives.',
        'Show risk notes such as low uniqueness or deep DOM context.',
        'Offer code generation for multiple language targets.',
        'Provide page highlighting and session management controls.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, bullet), bulletType='bullet', value='•') for item in fr],
            bulletType='bullet',
        )
    )
    story.append(Paragraph('Non-functional Requirements', h2))
    nfr = [
        'Local execution only; no external backend dependency required.',
        'Fast response during page analysis.',
        'Clear and simple user interface.',
        'Reliable match verification for selector quality.',
        'Graceful handling of login pages, iframes, and shadow DOM.',
        'Maintainable and testable architecture.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, bullet), bulletType='bullet', value='•') for item in nfr],
            bulletType='bullet',
        )
    )
    story.append(Paragraph('Project Deliverables', h2))
    pd = [
        'Browser-backed app for locator discovery.',
        'Final ranked selector output.',
        'Ready-to-use Selenium snippets.',
        'Manual and automated validation.',
        'Documentation and setup instructions.',
    ]
    story.append(
        ListFlowable(
            [ListItem(Paragraph(item, bullet), bulletType='bullet', value='•') for item in pd],
            bulletType='bullet',
        )
    )
    story.append(Paragraph('Security and Scope Considerations', h2))
    story.append(
        Paragraph(
            'The application runs locally and does not upload page content to an external service. It relies on the browser session to inspect the page DOM in a real environment. Users are responsible for validating secure or restricted pages before automation.',
            body,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph('Conclusion', h1))
    story.append(
        Paragraph(
            'The Locator Finder Agent is a practical local tool for discovering robust web element locators from real pages. It combines browser automation, live DOM analysis, match verification, selector ranking, and code generation in a single workflow. The project is especially useful for automation engineers, QA teams, and developers who need a faster and more reliable way to identify selectors for web testing and UI automation.',
            body,
        )
    )
    story.append(Paragraph('Thank you', h2))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    doc.build(story)


if __name__ == '__main__':
    output_path = r'C:\Users\1000050988\Downloads\project_evaluation_documentation.pdf'
    build_document(output_path)
    print(f'PDF generated: {output_path}')
