from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import re
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PCOMBA_O_URL="https://www.shiksha.com/executive-mba-chp"
PCOMBA_S_URL="https://www.shiksha.com/executive-mba-syllabus-chp"
PCOMBA_CAREER_URL = "https://www.shiksha.com/executive-mba-career-chp"
PCOMBA_EMBA_Admission_2025_URL = "https://www.shiksha.com/executive-mba-admission-chp"
PCOMBA_EMBA_DEFENCE_PERSOINAL = "https://www.shiksha.com/business-management-studies/articles/mba-for-defence-personnel-a-promising-start-to-second-innings-blogId-12931"
PCOMBA_FEES_URL = "https://www.shiksha.com/executive-mba-fees-chp"
EMBA_Rising_Demand_url="https://www.shiksha.com/news/business-management-studies-executive-mba-demand-surge-60-of-professionals-turning-to-iims-for-career-advancement-blogId-192324"


def create_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# ---------------- UTILITIES ----------------
def scroll_to_bottom(driver, scroll_times=3, pause=1.5):
    for _ in range(scroll_times):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(pause)




def extract_course_data(driver):
    driver.get(PCOMBA_O_URL)
    WebDriverWait(driver, 15)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    data = {}

    # -------------------------------
    wrapper = soup.find("div", class_="f48b")
    if not wrapper:
        return data

    # ----------------------
    # LAST UPDATED DATE
    updated_div = wrapper.find("div")
    if updated_div:
        span = updated_div.find("span")
        if span:
            data["last_updated"] = span.get_text(strip=True)

    # ----------------------
    # AUTHOR DETAILS
    author_p = wrapper.find("p", class_="_7417")
    if author_p:
        author_link = author_p.find("a")
        if author_link:
            data["author_name"] = author_link.get_text(strip=True)

        designation = author_p.find("span", class_="b0fc")
        if designation:
            data["author_designation"] = designation.get_text(strip=True)
    # Course Name
    course_name_div = soup.find("div", class_="a54c")
    if course_name_div and course_name_div.find("h1"):
        data["title"] = course_name_div.find("h1").get_text(strip=True)

    # -------------------------------
    # Overview section
    wrapper = soup.find("div", id="wikkiContents_chp_section_overview_0")
    if wrapper:
        content = wrapper.find("div", recursive=False)
        if content:
            latest_updates = extract_latest_updates(content)

            description = []
            important_links = []
            highlight_rows = []

            table = content.find("table")
            skip_mode = False  # for Latest Updates block

            for elem in content.children:
                if not hasattr(elem, "name"):
                    continue

                # Stop collecting description once table starts
                if elem.name == "table":
                    break

                # Detect Latest Updates heading
                if elem.name == "p" and "Latest Updates" in elem.get_text():
                    skip_mode = True
                    continue

                # Skip UL of latest updates
                if skip_mode and elem.name == "ul":
                    skip_mode = False
                    continue

                # Skip ads / iframe / video / quick links
                if elem.name in ["div", "iframe"]:
                    continue

                if elem.name == "p":
                    text = elem.get_text(" ", strip=True)

                    if not text:
                        continue
                    if text.startswith("Quick Links"):
                        continue
                    if text.startswith("Note:"):
                        continue

                    description.append(text)

            # -------------------------------
            # IMPORTANT LINKS (only from Quick Links section)
            for p in content.find_all("p"):
                a = p.find("a", href=True)
                if a and a.get_text(strip=True):
                    important_links.append({
                        "title": a.get_text(strip=True),
                        "url": a["href"]
                    })

            # -------------------------------
            # HIGHLIGHTS TABLE
            if table:
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all(["td", "th"])
                    if len(cols) == 2:
                        highlight_rows.append({
                            "Particular": cols[0].get_text(" ", strip=True),
                            "Details": cols[1].get_text(" ", strip=True)
                        })

            data["overviews"] = {
                "description": description,
                "latest_updates": latest_updates,
                "important_links": important_links,
                "highlights": {
                    "columns": ["Particular", "Details"],
                    "rows": highlight_rows
                }
            }

    # -------------------------------
    # Executive MBA Eligibility and Admission Section
    eligibility_section = soup.find("section", id="chp_section_eligibility")
    if eligibility_section:
        eligibility_content = eligibility_section.find("div", class_="_subcontainer")
        if eligibility_content:
            eligibility_texts = []
            admission_texts = []
            faqs = []

            # Extract all paragraphs under eligibility/admission
            for elem in eligibility_content.find_all(["p", "li", "h2"]):
                tag_text = elem.get_text(" ", strip=True)
                if elem.name == "h2" and "Admission" in tag_text:
                    current_block = admission_texts
                    continue
                if elem.name in ["p", "li"]:
                    if "Admission" in tag_text or admission_texts:
                        admission_texts.append(tag_text)
                    else:
                        eligibility_texts.append(tag_text)

            # Extract FAQs
            faq_divs = eligibility_content.find_all("div", class_="listener")
            for faq in faq_divs:
                question = faq.find("strong", class_="flx-box")
                answer_div = faq.find_next_sibling("div", class_="_16f53f")
                answer = answer_div.get_text(" ", strip=True) if answer_div else ""
                if question:
                    faqs.append({
                        "question": question.get_text(" ", strip=True),
                        "answer": answer
                    })

            data["eligibility_admission"] = {
                "eligibility": eligibility_texts,
                "admission": admission_texts,
                "faqs": faqs
            }
       # -------------------------------
    # Executive MBA Entrance Exams Section
    popular_exam_section = soup.find("section", id="chp_section_popularexams")
    if popular_exam_section:
        exam_data = {
            "intro": [],
            "exams_table": [],
            "quick_links": [],
            "important_exam_dates": {
                "upcoming": [],
                "past": []
            },
            "faqs": []
        }


        # -------------------------------
        # Intro (Clean & Non-repeating)
        intro_wrapper = popular_exam_section.find(
            "div", id="wikkiContents_chp_section_popularexams_0"
        )

        if intro_wrapper:
            inner_div = intro_wrapper.find("div", recursive=False)

            if inner_div:
                for elem in inner_div.children:
                    if not hasattr(elem, "name"):
                        continue

                    # Stop once table starts
                    if elem.name == "table":
                        break

                    # Only pick meaningful paragraphs
                    if elem.name == "p":
                        text = elem.get_text(" ", strip=True)

                        if not text:
                            continue
                        if text.startswith("Note:"):
                            continue
                        if "Quick Links" in text:
                            continue

                        exam_data["intro"].append(text)

        # -------------------------------
        # Exams Table
        table = popular_exam_section.find("table")
        if table:
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all(["td", "th"])
                if len(cols) == 3:
                    exam_data["exams_table"].append({
                        "exam_name": cols[0].get_text(" ", strip=True),
                        "exam_dates": cols[1].get_text(" ", strip=True),
                        "schedule_link": cols[2].get_text(" ", strip=True)
                    })

        # -------------------------------
        # Quick Links
        for a in popular_exam_section.find_all("a", href=True):
            title = a.get_text(strip=True)
            url = a["href"]
            if "mock" in title.lower() or "paper" in title.lower():
                exam_data["quick_links"].append({
                    "title": title,
                    "url": url
                })

        # -------------------------------
        # Important Exam Dates (Upcoming & Past)
        exam_tables = popular_exam_section.find_all("table", class_="upcomming-events")
        for table in exam_tables:
            is_past = "past-events" in table.get("class", [])
            rows = table.find_all("tr")[1:]
            for row in rows:
                cols = row.find_all("td")
                if len(cols) == 2:
                    record = {
                        "date": cols[0].get_text(" ", strip=True),
                        "event": cols[1].get_text(" ", strip=True)
                    }
                    if is_past:
                        exam_data["important_exam_dates"]["past"].append(record)
                    else:
                        exam_data["important_exam_dates"]["upcoming"].append(record)

        # -------------------------------
        # FAQs
        faq_questions = popular_exam_section.find_all("div", class_="listener")
        for q in faq_questions:
            question = q.get_text(" ", strip=True)
            ans_div = q.find_next_sibling("div", class_="_16f53f")
            answer = ans_div.get_text(" ", strip=True) if ans_div else ""
            exam_data["faqs"].append({
                "question": question,
                "answer": answer
            })

        data["executive_mba_entrance_exams"] = exam_data
    
    course_syllabus = {
    "intro": [],
    "common_topics_intro": [],
    "syllabus_table": {},
    "note": ""
    }
    
    syllabus_section = soup.find("section", id="chp_section_coursesyllabus")
    
    if syllabus_section:
        content_wrapper = syllabus_section.find(
            "div", id="wikkiContents_chp_section_coursesyllabus_0"
        )
    
        if content_wrapper:
            main_div = content_wrapper.find("div", recursive=False)
    
            current_semester = None
    
            for elem in main_div.children:
                if not hasattr(elem, "name"):
                    continue
    
                # -------------------------
                # INTRO PARAGRAPHS (TOP ONLY)
                if elem.name == "p":
                    text = elem.get_text(" ", strip=True)
    
                    if not text:
                        continue
    
                    # Note
                    if text.lower().startswith("note:"):
                        course_syllabus["note"] = text
                        continue
    
                    # Stop intro before table
                    if elem.find_next_sibling("table"):
                        course_syllabus["common_topics_intro"].append(text)
                    else:
                        course_syllabus["intro"].append(text)
    
                # -------------------------
                # SYLLABUS TABLE
                elif elem.name == "table":
                    rows = elem.find_all("tr")
    
                    for row in rows:
                        headers = row.find_all("th")
                        cols = row.find_all("td")
    
                        # Semester heading
                        if headers:
                            semester_text = headers[0].get_text(" ", strip=True)
                            current_semester = semester_text
                            course_syllabus["syllabus_table"][current_semester] = []
    
                        # Subjects
                        elif cols and current_semester:
                            for col in cols:
                                subject = col.get_text(" ", strip=True)
                                if subject:
                                    course_syllabus["syllabus_table"][current_semester].append(subject)
    
                # -------------------------
                # STOP when embeds / links start
                elif elem.name in ["div"] and elem.get("class") and "vcmsEmbed" in elem.get("class"):
                    break
        # -------------------------
    # COURSE SYLLABUS FAQs
    course_syllabus_faqs = []
    
    faq_section = syllabus_section.find("div", id="sectional-faqs-0")
    
    if faq_section:
        faq_items = faq_section.find_all("div", class_="html-0")
    
        for faq in faq_items:
            # Question
            question_text = faq.get_text(" ", strip=True)
            question_text = question_text.replace("Q:", "").strip()
    
            # Answer container is next sibling
            answer_container = faq.find_next_sibling("div", class_="_16f53f")
    
            if not answer_container:
                continue
    
            answer_paras = answer_container.select(
                ".cmsAContent p"
            )
    
            answer_texts = []
            for p in answer_paras:
                text = p.get_text(" ", strip=True)
                if not text:
                    continue
                if "Hope this helps" in text:
                    continue
    
                answer_texts.append(text)
    
            if question_text and answer_texts:
                course_syllabus_faqs.append({
                    "question": question_text,
                    "answer": " ".join(answer_texts)
                })

        data["course_syllabus"]=course_syllabus
        data["course_syllabus"]["faqs"] = course_syllabus_faqs
    
    specialization_section = soup.find("section", id="chp_section_popularspecialization")
    
    course_specialization = {
        "intro": [],
        "specializations_table": [],
        "note": "",
        "faqs": []
    }
    
    if specialization_section:
        content_wrapper = specialization_section.find(
            "div", id="wikkiContents_chp_section_popularspecialization_0"
        )
    
        if content_wrapper:
            main_div = content_wrapper.find("div", recursive=False)
    
            for elem in main_div.children:
                if not hasattr(elem, "name"):
                    continue
    
                # -------------------------
                # INTRO PARAGRAPHS
                if elem.name == "p":
                    text = elem.get_text(" ", strip=True)
    
                    if not text:
                        continue
    
                    if text.lower().startswith("note:"):
                        course_specialization["note"] = text
                        continue
    
                    course_specialization["intro"].append(text)
    
                # -------------------------
                # SPECIALIZATION TABLE
                elif elem.name == "table":
                    rows = elem.find_all("tr")
    
                    for row in rows[1:]:  # skip header
                        cols = row.find_all("td")
    
                        if len(cols) >= 2:
                            specialization = cols[0].get_text(" ", strip=True)
                            details = cols[1].get_text(" ", strip=True)
    
                            course_specialization["specializations_table"].append({
                                "specialization": specialization,
                                "details": details
                            })
    
        # -------------------------
        # FAQ SECTION
        faq_section = specialization_section.find("div", class_="sectional-faqs")
    
        if faq_section:
            questions = faq_section.find_all("div", class_="listener")
    
            for q in questions:
                question_text = q.get_text(" ", strip=True).replace("Q:", "").strip()
    
                answer_div = q.find_next_sibling("div", class_="_16f53f")
                answer_text = ""
    
                if answer_div:
                    answer_text = answer_div.get_text(" ", strip=True)
                    answer_text = answer_text.replace("A:", "").strip()
    
                course_specialization["faqs"].append({
                    "question": question_text,
                    "answer": answer_text
                })
    
    # finally add to main data
    data["course_specialization"] = course_specialization
    section = soup.find("section", id="chp_section_topratecourses")
    
    topratecourses = {
        "intro": [],
        "types": [],
        "popular_courses": [],
        "faqs": []
    }
    
    if section:
        wrapper = section.find("div", id="wikkiContents_chp_section_topratecourses_0")
    
        # ==========================
        # MAIN CONTENT (INTRO + TYPES)
        if wrapper:
            main_div = wrapper.find("div", recursive=False)
    
            current_type = None
    
            for elem in main_div.children:
                if not hasattr(elem, "name"):
                    continue
    
                # --------------------------
                # INTRO (before first h3)
                if elem.name == "p" and not topratecourses["types"]:
                    text = elem.get_text(" ", strip=True)
                    if text:
                        topratecourses["intro"].append(text)
    
                # --------------------------
                # TYPE HEADING
                elif elem.name == "h3":
                    if current_type:
                        topratecourses["types"].append(current_type)
    
                    current_type = {
                        "title": elem.get_text(" ", strip=True),
                        "description": [],
                        "table": [],
                        "note": ""
                    }
    
                # --------------------------
                # PARAGRAPHS INSIDE TYPE
                elif elem.name == "p" and current_type:
                    text = elem.get_text(" ", strip=True)
    
                    if not text:
                        continue
    
                    if text.lower().startswith("note:"):
                        current_type["note"] = text
                    else:
                        current_type["description"].append(text)
    
                # --------------------------
                # TABLE INSIDE TYPE
                elif elem.name == "table" and current_type:
                    rows = elem.find_all("tr")
    
                    headers = [
                        th.get_text(" ", strip=True)
                        for th in rows[0].find_all("th")
                    ]
    
                    for row in rows[1:]:
                        cols = row.find_all("td")
                        if len(cols) != len(headers):
                            continue
    
                        row_data = {}
                        for i, col in enumerate(cols):
                            row_data[headers[i]] = col.get_text(" ", strip=True)
    
                        current_type["table"].append(row_data)
    
            if current_type:
                topratecourses["types"].append(current_type)
    
        # ==========================
        # POPULAR COURSES (RIGHT SIDEBAR)
        popular_box = section.find("ul", class_="specialization-list")
    
        if popular_box:
            for li in popular_box.find_all("li", recursive=False):
                title_tag = li.find("strong")
                course_link = li.find("a", href=True)
    
                offered_by = li.find("label", class_="grayLabel")
                rating = li.find("span", class_="rating-block")
                reviews = li.find("a", class_="view_rvws")
    
                topratecourses["popular_courses"].append({
                    "course_name": title_tag.get_text(strip=True) if title_tag else "",
                    "course_url": course_link["href"] if course_link else "",
                    "offered_by": offered_by.find_parent("a").get_text(" ", strip=True) if offered_by else "",
                    "rating": rating.get_text(strip=True) if rating else "",
                    "reviews": reviews.get_text(strip=True) if reviews else ""
                })
    
        # ==========================
        # FAQs
        faq_section = section.find("div", class_="sectional-faqs")
    
        if faq_section:
            questions = faq_section.find_all("div", class_="listener")
    
            for q in questions:
                question = q.get_text(" ", strip=True).replace("Q:", "").strip()
    
                answer_div = q.find_next_sibling("div", class_="_16f53f")
                answer = ""
    
                if answer_div:
                    answer = answer_div.get_text(" ", strip=True)
                    answer = answer.replace("A:", "").strip()
    
                topratecourses["faqs"].append({
                    "question": question,
                    "answer": answer
                })
    
    # ADD TO MAIN DATA
    data["topratecourses"] = topratecourses
                

    return data

def extract_latest_updates(content):
    latest_updates = []

    latest_p = content.find(
        "p",
        string=lambda x: x and "Latest Updates" in x
    )
    if not latest_p:
        return latest_updates

    updates_ul = latest_p.find_next_sibling("ul")
    if not updates_ul:
        return latest_updates

    for li in updates_ul.find_all("li"):  # ✅ recursive=True by default
        text = li.get_text(" ", strip=True)

        if not text or len(text) < 20:
            continue

        a = li.find("a", href=True)
        link = None
        if a:
            link = {
                "title": a.get_text(strip=True),
                "url": a["href"]
            }

        latest_updates.append({
            "text": text,
            "link": link
        })

    return latest_updates

def scrape_syllabus_overview(driver):
    driver.get(PCOMBA_S_URL)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    section = soup.find("section", id="chp_syllabus_overview")

    data = {
        "last_updated":[],
        "author_name":[],
        "author_designation":[],
        "intro": [],
        "sections": []
    }
    if not section:
       return data
    course_name_div = soup.find("div", class_="a54c")
    if course_name_div and course_name_div.find("h1"):
        data["title"] = course_name_div.find("h1").get_text(strip=True)

    # -------------------------------
    wrapper = section.find("div", class_="f48b")
    if not wrapper:
        return data

    # ----------------------
    # LAST UPDATED DATE
    updated_div = wrapper.find("div")
    if updated_div:
        span = updated_div.find("span")
        if span:
            data["last_updated"] = span.get_text(strip=True)

    # ----------------------
    # AUTHOR DETAILS
    author_p = wrapper.find("p", class_="_7417")
    if author_p:
        author_link = author_p.find("a")
        if author_link:
            data["author_name"] = author_link.get_text(strip=True)

        designation = author_p.find("span", class_="b0fc")
        if designation:
            data["author_designation"] = designation.get_text(strip=True)

    content_div = section.find("div", id="wikkiContents_chp_syllabus_overview_0")
    if not content_div:
        return data

    current_section = None

    for elem in content_div.find("div", recursive=False).children:
        if not hasattr(elem, "name"):
            continue

        # =====================
        # INTRO (Before first H2)
        if elem.name == "p" and current_section is None:
            if elem.find("iframe"):
                continue

            text = elem.get_text(" ", strip=True)
            if text:
                data["intro"].append(text)

        # =====================
        # SECTION HEADING
        elif elem.name == "h2":
            if current_section:
                data["sections"].append(current_section)

            current_section = {
                "title": elem.get_text(" ", strip=True),
                "content": [],
                "tables": [],
                "lists": [],
                "note": ""
            }

        # =====================
        # PARAGRAPH
        elif elem.name == "p" and current_section:
            text = elem.get_text(" ", strip=True)
            if not text:
                continue

            if text.lower().startswith("note:"):
                current_section["note"] = text
            else:
                current_section["content"].append(text)

        # =====================
        # TABLE
        elif elem.name == "table" and current_section:
        
            # Detect EMBA syllabus table
            first_th = elem.find("th")
            if first_th and "Term" in first_th.get_text():
                parsed_table = parse_emba_syllabus_table(elem)
                current_section["tables"].append(parsed_table)
        
            else:
                # Normal table (keep your old logic)
                table_data = []
                rows = elem.find_all("tr")
                headers = [th.get_text(" ", strip=True) for th in rows[0].find_all("th")]
        
                for row in rows[1:]:
                    cols = row.find_all("td")
                    if not cols:
                        continue
        
                    row_obj = {}
                    for i, col in enumerate(cols):
                        key = headers[i] if i < len(headers) else f"col_{i+1}"
                        row_obj[key] = col.get_text(" ", strip=True)
        
                    table_data.append(row_obj)
        
                if table_data:
                    current_section["tables"].append(table_data)

        # =====================
        # LISTS
        elif elem.name == "ul" and current_section:
            items = [
                li.get_text(" ", strip=True)
                for li in elem.find_all("li")
                if li.get_text(strip=True)
            ]

            if items:
                current_section["lists"].append(items)

    if current_section:
        data["sections"].append(current_section)

    return data

def parse_emba_syllabus_table(table):
    syllabus = {}
    current_terms = []

    rows = table.find_all("tr")

    for row in rows:
        headers = row.find_all("th")
        cols = row.find_all("td")

        # -----------------------
        # HEADER ROW (Term X)
        if headers:
            current_terms = []
            for th in headers:
                term = th.get_text(" ", strip=True)
                if term:
                    syllabus.setdefault(term, [])
                    current_terms.append(term)

        # -----------------------
        # DATA ROW
        elif cols and current_terms:
            for i, col in enumerate(cols):
                if i >= len(current_terms):
                    continue

                value = col.get_text(" ", strip=True)
                if value and value != "-":
                    syllabus[current_terms[i]].append(value)

    return syllabus

def scrape_career_overview(driver):
    driver.get(PCOMBA_CAREER_URL)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    section = soup.find("section", id="chp_career_overview")

    data = {
        "last_updated": "",
        "author_name": "",
        "author_designation": "",
        "intro": [],
        "sections": []
    }
    
    if not section:
        return data
    course_name_div = soup.find("div", class_="a54c")
    if course_name_div and course_name_div.find("h1"):
        data["title"] = course_name_div.find("h1").get_text(strip=True)
    
    # -------------------------------
    wrapper = section.find("div", class_="f48b")
    if not wrapper:
        return data

    # ----------------------
    # LAST UPDATED DATE
    updated_div = wrapper.find("div")
    if updated_div:
        span = updated_div.find("span")
        if span:
            data["last_updated"] = span.get_text(strip=True)

    # ----------------------
    # AUTHOR DETAILS
    author_p = wrapper.find("p", class_="_7417")
    if author_p:
        author_link = author_p.find("a")
        if author_link:
            data["author_name"] = author_link.get_text(strip=True)

        designation = author_p.find("span", class_="b0fc")
        if designation:
            data["author_designation"] = designation.get_text(strip=True)

    content_div = section.find("div", id="wikkiContents_chp_career_overview_0")
    if not content_div:
        return data

    current_section = None

    for elem in content_div.find("div", recursive=False).children:
        if not hasattr(elem, "name"):
            continue

        # =====================
        # INTRO (Before first H2)
        if elem.name == "p" and current_section is None:
            if elem.find("iframe"):
                continue

            text = elem.get_text(" ", strip=True)
            if text:
                data["intro"].append(text)

        # =====================
        # SECTION HEADING
        elif elem.name == "h2" or elem.name == "h3":
            if current_section:
                data["sections"].append(current_section)

            current_section = {
                "title": elem.get_text(" ", strip=True),
                "content": [],
                "tables": [],
                "lists": [],
                "note": ""
            }

        # =====================
        # PARAGRAPH
        elif elem.name == "p" and current_section:
            text = elem.get_text(" ", strip=True)
            if not text:
                continue

            if text.lower().startswith("note:") or text.lower().startswith("note :"):
                current_section["note"] = text
            else:
                current_section["content"].append(text)

        # =====================
        # TABLE
        elif elem.name == "table" and current_section:
            table_data = []
            rows = elem.find_all("tr")
            
            if not rows:
                continue
                
            # Check if table has headers
            headers = []
            first_row = rows[0]
            header_cells = first_row.find_all(["th", "td"])
            
            for i, cell in enumerate(header_cells):
                header_text = cell.get_text(" ", strip=True)
                if header_text:
                    headers.append(header_text)
                else:
                    headers.append(f"col_{i+1}")
            
            # Process data rows
            for row in rows:
                # Skip if this row was already used as header
                if row == first_row and any("th" in str(cell) for cell in row.find_all()):
                    continue
                    
                cols = row.find_all("td")
                if not cols:
                    continue
                
                row_obj = {}
                for i, col in enumerate(cols):
                    key = headers[i] if i < len(headers) else f"col_{i+1}"
                    row_obj[key] = col.get_text(" ", strip=True)
                
                table_data.append(row_obj)
            
            if table_data:
                current_section["tables"].append(table_data)

        # =====================
        # LISTS
        elif elem.name == "ul" and current_section:
            items = [
                li.get_text(" ", strip=True)
                for li in elem.find_all("li")
                if li.get_text(strip=True)
            ]

            if items:
                current_section["lists"].append(items)

    # Add the last section if exists
    if current_section:
        data["sections"].append(current_section)

    return data

def scrape_admission_overview(driver):
    driver.get(PCOMBA_EMBA_Admission_2025_URL)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    section = soup.find("section", id="chp_admission_overview")

    data = {
        "last_updated": "",
        "author_name": "",
        "author_designation": "",
        "intro": [],
        "sections": []
    }
    
    if not section:
        return data
    course_name_div = soup.find("div", class_="a54c")
    if course_name_div and course_name_div.find("h1"):
        data["title"] = course_name_div.find("h1").get_text(strip=True)
    
    # -------------------------------
    wrapper = section.find("div", class_="f48b")
    if not wrapper:
        return data

    # ----------------------
    # LAST UPDATED DATE
    updated_div = wrapper.find("div")
    if updated_div:
        span = updated_div.find("span")
        if span:
            data["last_updated"] = span.get_text(strip=True)

    # ----------------------
    # AUTHOR DETAILS
    author_p = wrapper.find("p", class_="_7417")
    if author_p:
        author_link = author_p.find("a")
        if author_link:
            data["author_name"] = author_link.get_text(strip=True)

        designation = author_p.find("span", class_="b0fc")
        if designation:
            data["author_designation"] = designation.get_text(strip=True)

    content_div = section.find("div", id="wikkiContents_chp_admission_overview_0")
    if not content_div:
        return data

    current_section = None

    for elem in content_div.find("div", recursive=False).children:
        if not hasattr(elem, "name"):
            continue

        # =====================
        # INTRO (Before first H2)
        if elem.name == "p" and current_section is None:
            if elem.find("iframe"):
                continue

            text = elem.get_text(" ", strip=True)
            if text:
                data["intro"].append(text)

        # =====================
        # SECTION HEADING (H2)
        elif elem.name == "h2":
            if current_section:
                data["sections"].append(current_section)

            current_section = {
                "title": elem.get_text(" ", strip=True),
                "content": [],
                "tables": [],
                "lists": [],
                "note": "",
                "subsections": []  # For h3 subsections
            }

        # =====================
        # SUBSECTION HEADING (H3)
        elif elem.name == "h3":
            if current_section:
                # Add a new subsection within current section
                subsection = {
                    "title": elem.get_text(" ", strip=True),
                    "content": [],
                    "tables": [],
                    "lists": [],
                    "note": ""
                }
                current_section["subsections"].append(subsection)
            else:
                # If no main section exists yet, create one with h3 as title
                current_section = {
                    "title": elem.get_text(" ", strip=True),
                    "content": [],
                    "tables": [],
                    "lists": [],
                    "note": "",
                    "subsections": []
                }

        # =====================
        # PARAGRAPH
        elif elem.name == "p" and current_section:
            text = elem.get_text(" ", strip=True)
            if not text:
                continue

            # Determine where to add content: main section or last subsection
            target = current_section
            if current_section["subsections"]:
                target = current_section["subsections"][-1]

            if text.lower().startswith("note:") or text.lower().startswith("note :"):
                target["note"] = text
            else:
                target["content"].append(text)

        # =====================
        # TABLE
        elif elem.name == "table" and current_section:
            table_data = []
            rows = elem.find_all("tr")
            
            if not rows:
                continue
                
            # Check if table has headers
            headers = []
            first_row = rows[0]
            header_cells = first_row.find_all(["th", "td"])
            
            for i, cell in enumerate(header_cells):
                header_text = cell.get_text(" ", strip=True)
                if header_text:
                    headers.append(header_text)
                else:
                    headers.append(f"col_{i+1}")
            
            # Process data rows
            for row in rows:
                # Skip if this row was already used as header
                if row == first_row and any("th" in str(cell) for cell in row.find_all()):
                    continue
                    
                cols = row.find_all("td")
                if not cols:
                    continue
                
                row_obj = {}
                for i, col in enumerate(cols):
                    key = headers[i] if i < len(headers) else f"col_{i+1}"
                    row_obj[key] = col.get_text(" ", strip=True)
                
                table_data.append(row_obj)
            
            if table_data:
                # Determine where to add table: main section or last subsection
                if current_section["subsections"]:
                    current_section["subsections"][-1]["tables"].append(table_data)
                else:
                    current_section["tables"].append(table_data)

        # =====================
        # LISTS
        elif elem.name in ["ul", "ol"] and current_section:
            items = [
                li.get_text(" ", strip=True)
                for li in elem.find_all("li")
                if li.get_text(strip=True)
            ]

            if items:
                # Determine where to add list: main section or last subsection
                if current_section["subsections"]:
                    current_section["subsections"][-1]["lists"].append(items)
                else:
                    current_section["lists"].append(items)

    # Add the last section if exists
    if current_section:
        data["sections"].append(current_section)

    return data


def scrape_fees_overview(driver):
    driver.get(PCOMBA_FEES_URL)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    section = soup.find("section", id="chp_fees_overview")

    data = {
        "last_updated": "",
        "author_name": "",
        "author_designation": "",
        "intro": [],
        "sections": []
    }
    
    if not section:
        return data
    course_name_div = soup.find("div", class_="a54c")
    if course_name_div and course_name_div.find("h1"):
        data["title"] = course_name_div.find("h1").get_text(strip=True)
    
    # -------------------------------
    wrapper = section.find("div", class_="f48b")
    if not wrapper:
        return data

    # ----------------------
    # LAST UPDATED DATE
    updated_div = wrapper.find("div")
    if updated_div:
        span = updated_div.find("span")
        if span:
            data["last_updated"] = span.get_text(strip=True)

    # ----------------------
    # AUTHOR DETAILS
    author_p = wrapper.find("p", class_="_7417")
    if author_p:
        author_link = author_p.find("a")
        if author_link:
            data["author_name"] = author_link.get_text(strip=True)

        designation = author_p.find("span", class_="b0fc")
        if designation:
            data["author_designation"] = designation.get_text(strip=True)

    content_div = section.find("div", id="wikkiContents_chp_fees_overview_0")
    if not content_div:
        return data

    current_section = None

    for elem in content_div.find("div", recursive=False).children:
        if not hasattr(elem, "name"):
            continue

        # =====================
        # INTRO (Before first H2)
        if elem.name == "p" and current_section is None:
            # Skip iframes and empty paragraphs
            if elem.find("iframe") or not elem.get_text(strip=True):
                continue

            text = elem.get_text(" ", strip=True)
            # Skip if it's just a link
            if text and not text.startswith("http") and not text.startswith("Helpful Links"):
                data["intro"].append(text)

        # =====================
        # SECTION HEADING
        elif elem.name == "h2":
            if current_section:
                data["sections"].append(current_section)

            current_section = {
                "title": elem.get_text(" ", strip=True),
                "content": [],
                "tables": [],
                "lists": [],
                "note": ""
            }

        # =====================
        # PARAGRAPH
        elif elem.name == "p" and current_section:
            # Skip iframes and empty paragraphs
            if elem.find("iframe") or not elem.get_text(strip=True):
                continue
                
            text = elem.get_text(" ", strip=True)
            if not text:
                continue

            # Check for note/source
            if text.lower().startswith("source") or text.lower().startswith("note:"):
                current_section["note"] = text
            # Skip link paragraphs and "Helpful Links" section
            elif text.startswith("http") or text.startswith("Helpful Links"):
                continue
            # Skip if it looks like a table caption or list heading
            elif "Here is the list" in text or "Take a look at" in text:
                continue
            else:
                current_section["content"].append(text)

        # =====================
        # TABLE
        elif elem.name == "table" and current_section:
            table_data = []
            rows = elem.find_all("tr")
            
            if not rows:
                continue
                
            # Check if table has headers
            headers = []
            first_row = rows[0]
            header_cells = first_row.find_all(["th", "td"])
            
            for i, cell in enumerate(header_cells):
                header_text = cell.get_text(" ", strip=True)
                if header_text:
                    headers.append(header_text)
                else:
                    headers.append(f"col_{i+1}")
            
            # Process data rows
            for row in rows:
                # Skip if this row was already used as header
                if row == first_row and any("th" in str(cell) for cell in row.find_all()):
                    continue
                    
                cols = row.find_all("td")
                if not cols:
                    continue
                
                row_obj = {}
                for i, col in enumerate(cols):
                    key = headers[i] if i < len(headers) else f"col_{i+1}"
                    # Extract only text, ignore links
                    row_obj[key] = col.get_text(" ", strip=True)
                
                table_data.append(row_obj)
            
            if table_data:
                current_section["tables"].append(table_data)

        # =====================
        # LISTS
        elif elem.name == "ul" and current_section:
            items = [
                li.get_text(" ", strip=True)
                for li in elem.find_all("li")
                if li.get_text(strip=True)
            ]

            if items:
                current_section["lists"].append(items)

        # =====================
        # IFRAME (Video)
        elif elem.name == "iframe" and current_section:
            # Store iframe/video information separately
            video_info = {
                "src": elem.get("src", ""),
                "width": elem.get("width", ""),
                "height": elem.get("height", ""),
                "title": elem.get("title", "")
            }
            if "video_info" not in current_section:
                current_section["video_info"] = []
            current_section["video_info"].append(video_info)

    # Add the last section if exists
    if current_section:
        data["sections"].append(current_section)

    return data

def scrape_article_content(driver):
    driver.get(PCOMBA_EMBA_DEFENCE_PERSOINAL)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Create a clean data structure
    article_data = {
        "title":"",
        "author_name": "",
        "author_designation": "",
        "last_updated": "",
        "summary": "",
        "sections": [],
        "faqs": [],
        "related_colleges": [],
        "table_of_contents": [],
        "comments": [],
        "author_bio": "",
        "download_pdf": "",
        "images": []
    }
    title = soup.find("div",class_="adp_blog")
    h1 = title.find("h1").text.strip()
    article_data["title"]=h1
    # ----------------------
    # AUTHOR DETAILS
    author_div = soup.find("div", class_="adp_user_tag")
    if author_div:
        author_link = author_div.find("a", class_="user-img")
        if author_link:
            author_name_div = author_div.find_next("div", class_="adp_usr_dtls")
            if author_name_div:
                name_link = author_name_div.find("a")
                if name_link:
                    article_data["author_name"] = name_link.get_text(strip=True)
                
                designation_div = author_name_div.find("div", class_="user_expert_level")
                if designation_div:
                    article_data["author_designation"] = designation_div.get_text(strip=True)

    # ----------------------
    # LAST UPDATED DATE
    updated_div = soup.find("div", class_="blogdata_user")
    if updated_div:
        span = updated_div.find("span")
        if span:
            update_text = span.get_text(strip=True)
            if "Updated on" in update_text:
                article_data["last_updated"] = update_text.replace("Updated on ", "")

    # ----------------------
    # SUMMARY
    summary_div = soup.find("div", class_="blogSummary")
    if summary_div:
        article_data["summary"] = summary_div.get_text(strip=True)

    # ----------------------
    # IMAGES
    photo_widgets = soup.find_all("div", class_="photo-widget-full")
    for widget in photo_widgets:
        img = widget.find("img")
        if img:
            caption = widget.find("strong", class_="_img-caption")
            image_info = {
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "caption": caption.get_text(strip=True) if caption else ""
            }
            article_data["images"].append(image_info)

    # ----------------------
    # MAIN CONTENT SECTIONS
    main_content_div = soup.find("div", id="blogId-12931")
    if main_content_div:
        # Get all wikicontents divs that contain sections
        wikicontents_divs = main_content_div.find_all("div", class_="wikkiContents")
        
        for content_div in wikicontents_divs:
            # Skip FAQ and other special divs
            if "faqAccordian" in content_div.get("class", []):
                # Check if it has h2 headings
                h2_headings = content_div.find_all("h2")
                
                for h2 in h2_headings:
                    section = {
                        "title": h2.get_text(" ", strip=True),
                        "content": [],
                    }
                    
                    # Get all content after h2 until next h2
                    next_elem = h2.next_sibling
                    while next_elem and (not hasattr(next_elem, 'name') or next_elem.name != 'h2'):
                        if hasattr(next_elem, 'name'):
                            if next_elem.name == 'p':
                                text = next_elem.get_text(" ", strip=True)
                                if text and not text.startswith("http"):
                                    section["content"].append(text)
                            elif next_elem.name in ['ul', 'ol']:
                                items = [
                                    li.get_text(" ", strip=True)
                                    for li in next_elem.find_all("li")
                                    if li.get_text(strip=True)
                                ]
                                if items:
                                    section["lists"].append(items)
                        
                        next_elem = next_elem.next_sibling if next_elem else None
                    
                    article_data["sections"].append(section)

    # ----------------------
    # FAQ SECTION
    faq_sections = soup.find_all("div", class_="sectional-faqs")
    for faq_section in faq_sections:
        faq_items = faq_section.find_all("div", class_="c5db62")
        
        for faq_item in faq_items:
            question_elem = faq_item.find("strong", class_="flx-box")
            if question_elem:
                question_text = question_elem.get_text(" ", strip=True)
                # Clean question text
                if "Q:" in question_text:
                    question_text = question_text.split("Q:")[1].strip()
                
                # Find answer
                answer_div = faq_item.find_next("div", class_="_16f53f")
                if answer_div:
                    answer_content = answer_div.find("div", class_="cmsAContent")
                    if answer_content:
                        answer_text = answer_content.get_text(" ", strip=True)
                        
                        faq_data = {
                            "question": question_text,
                            "answer": answer_text
                        }
                        article_data["faqs"].append(faq_data)

    # ----------------------
    # TABLE OF CONTENTS
    toc_wrapper = soup.find("ul", id="tocWrapper")
    if toc_wrapper:
        toc_items = toc_wrapper.find_all("li")
        for item in toc_items:
            toc_text = item.get_text(strip=True)
            if toc_text:
                article_data["table_of_contents"].append(toc_text)

    # ----------------------
    # RELATED COLLEGES
    reco_section = soup.find("div", class_="recoWidgetSection")
    if reco_section:
        college_cards = reco_section.find_all("div", class_="collegCard")
        
        for card in college_cards:
            college_info = {}
            
            # College Name
            name_elem = card.find("strong", class_="mainH")
            if name_elem:
                name_link = name_elem.find("a")
                if name_link:
                    college_info["name"] = name_link.get_text(strip=True)
                    college_info["url"] = name_link.get("href", "")
            
            # Location
            location_elem = card.find("div", class_="location")
            if location_elem:
                location_name = location_elem.find("span", class_="locationName")
                if location_name:
                    college_info["location"] = location_name.get_text(strip=True)
            
            # Rank
            rank_elem = card.find("span", class_="rank")
            if rank_elem:
                college_info["rank"] = rank_elem.get_text(strip=True)
            
            # Fees
            fees_elem = card.find("span", class_="comma")
            if fees_elem:
                college_info["fees"] = fees_elem.get_text(strip=True)
            
            # Courses Offered
            courses_link = card.find("a", class_="link")
            if courses_link:
                college_info["courses_offered"] = courses_link.get_text(strip=True)
            
            if college_info:
                article_data["related_colleges"].append(college_info)

    # ----------------------
    # COMMENTS
    comments_div = soup.find("div", class_="ana-div")
    if comments_div:
        comment_items = comments_div.find_all("div", class_="qstn-div")
        
        for comment_item in comment_items:
            comment_data = {}
            
            # User info
            user_div = comment_item.find("div", class_="ana--comments_userdtls")
            if user_div:
                user_link = user_div.find("a")
                if user_link:
                    comment_data["user_name"] = user_link.get_text(strip=True)
                
                time_p = user_div.find("p", class_="ana--comments_time")
                if time_p:
                    comment_data["time"] = time_p.get_text(strip=True)
            
            # Comment text
            comment_content = comment_item.find("div", class_="commentContent")
            if comment_content:
                comment_data["comment"] = comment_content.get_text(strip=True)
            
            if comment_data:
                article_data["comments"].append(comment_data)

    # ----------------------
    # AUTHOR BIO
    author_bio_section = soup.find("div", class_="abt-athr-bio")
    if author_bio_section:
        bio_content = author_bio_section.find("div", class_="wikkiContents")
        if bio_content:
            # Get all paragraphs
            paragraphs = []
            for elem in bio_content.children:
                if hasattr(elem, 'name'):
                    if elem.name == 'p':
                        text = elem.get_text(strip=True)
                        if text and "Read Full Bio" not in text:
                            paragraphs.append(text)
                    elif elem.name == 'a' and "Read Full Bio" in elem.get_text():
                        break
            
            if paragraphs:
                article_data["author_bio"] = " ".join(paragraphs)

    # ----------------------
    # DOWNLOAD PDF
    download_btn = soup.find("div", class_="dnld-btn")
    if download_btn:
        pdf_link = download_btn.find("a", class_="button--orange")
        if pdf_link:
            article_data["download_pdf"] = pdf_link.get("href", "")

    # Create final output structure
    final_output = {
        "Executive MBA": {
            "EMBA for defence personal": article_data
        }
    }
    
    return final_output

def scrape_rising_content(driver):
    """
    Article को scrape करके structured data में convert करता है
    """
    from bs4 import BeautifulSoup
    
    driver.get(EMBA_Rising_Demand_url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    # Create a clean data structure
    article_data = {
        "title": "",
        "author_name": "",
        "author_designation": "",
        "last_updated": "",
        "summary": "",
        "sections": [],
        "images": [],
        "key_points": [],
        "related_articles": []
    }
    
    # ======================
    # 1. TITLE
    # ======================
    # Look for title in h1
    h1_tag = soup.find("h1")
    if h1_tag:
        article_data["title"] = h1_tag.text.strip()
    
    # ======================
    # 2. AUTHOR DETAILS
    # ======================
    author_div = soup.find("div", class_="adp_user_tag")
    if author_div:
        # Get author name
        author_name_div = author_div.find("div", class_="adp_usr_dtls")
        if author_name_div:
            name_link = author_name_div.find("a")
            if name_link:
                # Extract text before tick icon
                name_text = ""
                for content in name_link.contents:
                    if hasattr(content, 'name') and content.name == 'i':
                        break
                    if isinstance(content, str):
                        name_text += content
                article_data["author_name"] = name_text.strip()
            
            # Get designation
            designation_div = author_name_div.find("div", class_="user_expert_level")
            if designation_div:
                article_data["author_designation"] = designation_div.text.strip()
    
    # ======================
    # 3. LAST UPDATED DATE
    # ======================
    updated_div = soup.find("div", class_="blogdata_user")
    if updated_div:
        span = updated_div.find("span")
        if span:
            update_text = span.text.strip()
            article_data["last_updated"] = update_text
    
    # ======================
    # 4. SUMMARY (FROM blogSummary DIV) - EXACT MATCH
    # ======================
    summary_div = soup.find("div", class_="blogSummary")
    if summary_div:
        article_data["summary"] = summary_div.text.strip()
    
    # ======================
    # 5. IMAGES
    # ======================
    # Find all images in photo-widget-full
    photo_widgets = soup.find_all("div", class_="photo-widget-full")
    for widget in photo_widgets:
        img = widget.find("img")
        if img and img.get("src"):
            image_info = {
                "src": img.get("src"),
                "alt": img.get("alt", ""),
                "caption": ""
            }
            article_data["images"].append(image_info)
    
    # Also check for lazy images
    lazy_imgs = soup.find_all("img", class_="lazy")
    for img in lazy_imgs:
        src = img.get("src")
        if src and src not in [i["src"] for i in article_data["images"]]:
            image_info = {
                "src": src,
                "alt": img.get("alt", ""),
                "caption": ""
            }
            article_data["images"].append(image_info)
    
    # ======================
    # 6. MAIN CONTENT SECTIONS (FROM H2 HEADINGS)
    # ======================
    # Find all wikicontents divs
    wikicontents_divs = soup.find_all("div", class_="wikkiContents")
    
    section_counter = 0
    for content_div in wikicontents_divs:
        # Find all h2 headings in this div
        h2_headings = content_div.find_all("h2")
        
        if h2_headings:
            for h2 in h2_headings:
               
                
                # Extract section title (remove strong tags if present)
                title_text = h2.text.strip()
                if h2.find("strong"):
                    title_text = h2.find("strong").text.strip()
                
                section_data = {
                    "title": title_text,
                    "content": [],
                    "lists": [],
                }
                
                # Get all content after this h2 until next h2
                current_element = h2.next_sibling
                
                while current_element:
                    if hasattr(current_element, 'name'):
                        # Stop if we encounter another h2
                        if current_element.name == 'h2':
                            break
                        
                        # Paragraphs
                        if current_element.name == 'p':
                            text = current_element.text.strip()
                            if text:
                                section_data["content"].append(text)
                        
                        # Lists
                        elif current_element.name == 'ul':
                            list_items = []
                            li_elements = current_element.find_all("li")
                            for li in li_elements:
                                # Check if li contains a link (for related articles)
                                link = li.find("a")
                                if link and link.get("href") and "blogId" in link.get("href", ""):
                                    list_items.append(link.text.strip())
                                elif li.text.strip():
                                    list_items.append(li.text.strip())
                            
                            if list_items:
                                section_data["lists"].append(list_items)
                    
                    current_element = current_element.next_sibling
                
                # Only add section if it has content
                if section_data["content"] or section_data["lists"]:
                    article_data["sections"].append(section_data)
        
        # If no h2 but has paragraphs, check for content
        elif not h2_headings:
            paragraphs = content_div.find_all("p")
            for p in paragraphs:
                text = p.text.strip()
                if text and len(text) > 50 and "Read More" not in text:
                    # This might be introductory content
                    if not any(s["title"] == "Introduction" for s in article_data["sections"]):
                        section_data = {
                            "section_id": "section_intro",
                            "title": "Introduction",
                            "content": [text],
                            "lists": [],
                            "images": []
                        }
                        article_data["sections"].append(section_data)
                    break
    
    # ======================
    # 7. KEY POINTS (FROM STRONG TAGS IN ALL CONTENT)
    # ======================
    # Extract from main content div
    main_content_div = soup.find("div", id=lambda x: x and x.startswith("blogId-"))
    if main_content_div:
        # Get all strong tags
        strong_tags = main_content_div.find_all(["strong", "em"])
        
        for tag in strong_tags:
            text = tag.text.strip()
            # Filter conditions
            if text and len(text) > 5 and len(text) < 150:
                # Skip common phrases
                skip_phrases = ["Read More:", "Read More", "blogId", "utm_source", "http", "www."]
                if not any(skip in text for skip in skip_phrases):
                    # Avoid duplicates
                    if text not in article_data["key_points"]:
                        article_data["key_points"].append(text)
    
    # ======================
    # 8. RELATED COLLEGES (FROM COLLEGE CARDS)
    # ======================
    # Find college recommendation section
    reco_section = soup.find("div", class_="recoWidgetSection")
    if reco_section:
        college_cards = reco_section.find_all("div", class_="collegCard")
        
        for card in college_cards:
            college_info = {}
            
            # College Name
            header_box = card.find("div", class_="headerBox")
            if header_box:
                name_link = header_box.find("a", class_="blackLink")
                if name_link:
                    # Use title attribute if available, otherwise text
                    college_name = name_link.get("title", name_link.text.strip())
                    college_info["name"] = college_name
                    college_info["url"] = name_link.get("href", "")
            
            # Location
            location_div = card.find("div", class_="location")
            if location_div:
                location_span = location_div.find("span", class_="locationName")
                if location_span:
                    college_info["location"] = location_span.text.strip()
            
            # Rank
            rank_span = card.find("span", class_="rank")
            if rank_span:
                college_info["rank"] = rank_span.text.strip()
            
            # Fees
            fees_span = card.find("span", class_="comma")
            if fees_span:
                college_info["fees"] = fees_span.text.strip()
            
            # Rating
            rating_span = card.find("span", class_="starBox")
            if rating_span:
                college_info["rating"] = rating_span.text.strip()
            
            # Courses Offered
            courses_link = card.find("a", class_="link")
            if courses_link:
                college_info["courses_offered"] = courses_link.text.strip()
            
            if college_info:
                article_data["related_colleges"].append(college_info)
    
    # ======================
    # 9. RELATED ARTICLES (FROM "Read More" SECTION) - FIXED VERSION
    # ======================
    # FIX: Use string parameter instead of text
    read_more_elements = soup.find_all(string=lambda text: "Read More:" in str(text))
    
    for element in read_more_elements:
        parent = element.parent
        # Find all links in this section
        links = parent.find_all("a", href=True)
        
        for link in links:
            href = link.get("href", "")
            text = link.text.strip()
            
            # Check if it's a related article link
            if href and text and "blogId" in href:
                # Skip if it's the current article
                if not any(article_data["title"] in text for article_data in article_data["related_articles"]):
                    article_data["related_articles"].append({
                        "title": text,
                        "url": href
                    })
    
    # Alternative method to find related articles
    if not article_data["related_articles"]:
        # Look for unordered lists with article links
        ul_lists = soup.find_all("ul")
        for ul in ul_lists:
            links = ul.find_all("a", href=lambda x: x and "blogId" in x)
            for link in links[:3]:  # Limit to 3 per list
                href = link.get("href", "")
                text = link.text.strip()
                if href and text and len(text) > 10:
                    article_data["related_articles"].append({
                        "title": text,
                        "url": href
                    })
    
    # ======================
    # 10. TABLE OF CONTENTS
    # ======================
    toc_wrapper = soup.find("ul", id="tocWrapper")
    if toc_wrapper:
        toc_items = toc_wrapper.find_all("li")
        for item in toc_items:
            text = item.text.strip()
            if text:
                article_data["table_of_contents"].append(text)
    
    # ======================
    # 11. COMMENTS
    # ======================
    comments_div = soup.find("div", id="multiTag_comments")
    if comments_div:
        comment_items = comments_div.find_all("div", class_="qstn-div")
        for item in comment_items:
            comment_data = {}
            
            # User info
            user_div = item.find("div", class_="ana--comments_userdtls")
            if user_div:
                user_link = user_div.find("a")
                if user_link:
                    comment_data["user_name"] = user_link.text.strip()
                
                time_p = user_div.find("p", class_="ana--comments_time")
                if time_p:
                    comment_data["time"] = time_p.text.strip()
            
            # Comment text
            comment_content = item.find("div", class_="commentContent")
            if comment_content:
                comment_data["comment"] = comment_content.text.strip()
            
            if comment_data:
                article_data["comments"].append(comment_data)
    
    # ======================
    # 12. FAQ SECTION
    # ======================
    # Look for FAQ accordions
    faq_divs = soup.find_all("div", class_="faqAccordian")
    for faq_div in faq_divs:
        # Check for question-answer pairs
        questions = faq_div.find_all(["h3", "h4", "strong"])
        
        for q in questions:
            q_text = q.text.strip()
            if q_text and ("?" in q_text or q_text.lower().startswith(("what", "how", "why", "can", "is", "does"))):
                # Find answer
                answer = q.find_next("p")
                if not answer:
                    answer = q.find_next("div")
                
                if answer:
                    faq_data = {
                        "question": q_text,
                        "answer": answer.text.strip()
                    }
                    article_data["faqs"].append(faq_data)
    
    # ======================
    # 13. CLEANUP AND FINALIZATION
    # ======================
    # Remove empty sections
    article_data["sections"] = [s for s in article_data["sections"] 
                               if s.get("content") or s.get("lists")]
    
    # Remove duplicates from key points
    article_data["key_points"] = list(dict.fromkeys(article_data["key_points"]))
    
    # Filter key points (remove very short or very long)
    article_data["key_points"] = [kp for kp in article_data["key_points"] 
                                 if 10 <= len(kp) <= 100]
    
    # Limit related articles to 5
    article_data["related_articles"] = article_data["related_articles"][:5]
    
    # Create final output structure matching your JSON
    final_output = {
        "Executive MBA": {
            "EMBA_RISING_DEMANAD": {
              
                    "EMBA for defence personal": article_data

            }
        }
    }
    
    return final_output

    
def scrape_mba_colleges():
    driver = create_driver()

      

    try:
       data = {
              "Executive MBA":{
                   "overviews":extract_course_data(driver),
                   "syllabus":scrape_syllabus_overview(driver),
                   "career":scrape_career_overview(driver),

                   "EMBA_addmission_2025":scrape_admission_overview(driver),
                   "fees": scrape_fees_overview(driver),
                "EMBA_for_defence_personal":scrape_article_content(driver),
                "EMBA_RISING_DEMANAD":scrape_rising_content(driver)
                   }
                }
       
        
        # data["overview"] =  overviews
        # data["courses"] = courses

    finally:
        driver.quit()
    
    return data



import time

DATA_FILE =  "popular_mba_data.json"
UPDATE_INTERVAL = 6 * 60 * 60  # 6 hours

def auto_update_scraper():
    # Check last modified time
    # if os.path.exists(DATA_FILE):
    #     last_mod = os.path.getmtime(DATA_FILE)
    #     if time.time() - last_mod < UPDATE_INTERVAL:
    #         print("⏱️ Data is recent, no need to scrape")
    #         return

    print("🔄 Scraping started")
    data = scrape_mba_colleges()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ Data scraped & saved successfully")

if __name__ == "__main__":

    auto_update_scraper()

