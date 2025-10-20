#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "flask>=3.0.0",
#     "werkzeug>=3.0.0",
# ]
# ///

"""
Enhanced Sitemap Generator - Self-contained Flask app
- Creates locale-specific sitemaps
- Creates master sitemaps (all URLs combined)
- Separates paginated pages into their own sitemaps
"""

import os
from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify, flash
from werkzeug.utils import secure_filename
import csv
import sys
from collections import defaultdict, Counter
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import re
import gzip
import zipfile
import io
from urllib.parse import urlparse
import logging

app = Flask(__name__)
app.secret_key = 'sitemap_generator_secret_key_' + datetime.now().strftime('%Y%m%d')

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure necessary folders exist
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'xml_sitemaps'
RAW_OUTPUT_FOLDER = 'raw_xml_sitemaps'
MASTER_OUTPUT_FOLDER = 'master_xml_sitemaps'
MASTER_RAW_OUTPUT_FOLDER = 'master_raw_xml_sitemaps'
PAGINATED_OUTPUT_FOLDER = 'paginated_xml_sitemaps'
PAGINATED_RAW_OUTPUT_FOLDER = 'paginated_raw_xml_sitemaps'
LOG_FOLDER = 'logs'

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, RAW_OUTPUT_FOLDER, 
               MASTER_OUTPUT_FOLDER, MASTER_RAW_OUTPUT_FOLDER,
               PAGINATED_OUTPUT_FOLDER, PAGINATED_RAW_OUTPUT_FOLDER, LOG_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global variable to store progress
progress = {"status": "", "percentage": 0, "error": None}

# Sitemap limits per best practices
MAX_URLS_PER_SITEMAP = 50000
MAX_SITEMAP_SIZE_MB = 50

# Regex pattern for paginated pages
PAGINATION_PATTERN = re.compile(r'/Page-\d+', re.IGNORECASE)

def is_paginated_url(url):
    """Check if URL is a paginated page"""
    return bool(PAGINATION_PATTERN.search(url))

def format_number(num):
    """Format number with commas for readability"""
    return f"{num:,}"

def log_error(message):
    """Log errors to both file and progress"""
    logger.error(message)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_FOLDER, f"error_log_{timestamp}.txt")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now()}: {message}\n")
    progress["error"] = message
    flash(message, 'error')

def parse_homepage_csv(file_path):
    """Parse homepage CSV - supports multiple formats"""
    homepages = defaultdict(dict)
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            first_line = csvfile.readline().strip()
            if first_line.startswith('sep='):
                logger.info(f"Detected separator declaration: {first_line}, skipping it")
            else:
                csvfile.seek(0)
            
            reader = csv.DictReader(csvfile)
            fieldnames = list(reader.fieldnames)
            
            if fieldnames and 'sep=' in str(fieldnames[0]).lower():
                logger.error(f"Still detecting sep= in fieldnames after skip: {fieldnames}")
                raise ValueError("CSV parsing error: sep= declaration not properly skipped. Please resave your CSV file.")
            
            logger.info(f"Homepage CSV columns: {fieldnames}")
            
            has_country = 'Country' in fieldnames
            has_language = 'Language' in fieldnames
            has_section = 'Section' in fieldnames
            has_locale = 'Locale' in fieldnames
            
            if not has_country and not has_section:
                raise ValueError(f"Homepage CSV must have either 'Country' or 'Section' column. Found: {fieldnames}")
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    url = row.get('Homepage', '').rstrip('/')
                    if not url:
                        logger.warning(f"Row {row_num}: Empty homepage URL, skipping")
                        continue
                    
                    if has_country and has_language:
                        country = row.get('Country', '').lower()
                        language = row.get('Language', '').lower()
                        locale = row.get('Locale', '').lower()
                        is_default = row.get('Language Default', 'N') == 'Y'
                        
                        key = f"{language}-{country}" if not is_default else language
                        homepages[key] = {
                            'url': url,
                            'is_default': is_default,
                            'country': country,
                            'language': language,
                            'locale': locale
                        }
                    
                    elif has_section:
                        section = row.get('Section', '').replace(' ', '_')
                        locale = row.get('Locale', '').upper()
                        
                        key = locale.lower() if locale else section.lower()
                        homepages[key] = {
                            'url': url,
                            'is_default': False,
                            'country': locale,
                            'language': locale,
                            'locale': locale,
                            'section': section
                        }
                    
                    logger.info(f"Row {row_num}: Added homepage {key} -> {url}")
                    
                except Exception as e:
                    logger.error(f"Row {row_num}: Error parsing row: {str(e)}")
                    continue
        
        if not homepages:
            raise ValueError("No valid homepages found in CSV")
        
        logger.info(f"Successfully parsed {format_number(len(homepages))} homepages")
        return homepages
        
    except Exception as e:
        log_error(f"Error parsing homepage CSV: {str(e)}")
        raise

def find_url_column(fieldnames):
    """Find column containing URL data"""
    url_keywords = ['url', 'address', 'link', 'href', 'page']
    
    for field in fieldnames:
        field_lower = field.lower().replace(' ', '').replace('_', '')
        for keyword in url_keywords:
            if keyword in field_lower:
                return field
    return None

def find_indexability_column(fieldnames):
    """Find column containing indexability data"""
    indexability_keywords = ['indexability', 'indexable', 'index', 'status', 'indexation']
    
    for field in fieldnames:
        field_lower = field.lower().replace(' ', '').replace('_', '')
        for keyword in indexability_keywords:
            if keyword in field_lower:
                return field
    return None

def extract_url_pattern(url, base_domain):
    """Extract the path/pattern from a URL for matching across locales"""
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        parts = [p for p in path.split('/') if p]
        
        cleaned_parts = []
        skip_next = False
        
        for i, part in enumerate(parts):
            if skip_next:
                skip_next = False
                continue
            
            if len(part) == 2 and part.isupper():
                continue
            elif i < len(parts) - 1 and len(part) == 2 and len(parts[i+1]) <= 5:
                skip_next = True
                continue
            else:
                cleaned_parts.append(part)
        
        cleaned_path = '/' + '/'.join(cleaned_parts) if cleaned_parts else '/'
        
        if parsed.query:
            cleaned_path += '?' + parsed.query
        
        return cleaned_path
        
    except Exception as e:
        logger.warning(f"Error extracting pattern from {url}: {str(e)}")
        return urlparse(url).path

def parse_internal_csv(file_path, homepages):
    """Parse internal pages CSV - works with any domain"""
    pages = defaultdict(list)
    base_domains = set()
    
    for homepage_data in homepages.values():
        parsed = urlparse(homepage_data['url'])
        base_domains.add(f"{parsed.scheme}://{parsed.netloc}")
    
    logger.info(f"Base domains to process: {base_domains}")
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            first_line = csvfile.readline().strip()
            if first_line.startswith('sep='):
                logger.info(f"Detected separator declaration: {first_line}, skipping it")
            else:
                csvfile.seek(0)
            
            reader = csv.DictReader(csvfile)
            fieldnames = list(reader.fieldnames)
            
            if fieldnames and 'sep=' in str(fieldnames[0]).lower():
                logger.error(f"Still detecting sep= in fieldnames after skip: {fieldnames}")
                raise ValueError("CSV parsing error: sep= declaration not properly skipped. Please resave your CSV file.")
            
            logger.info(f"Internal CSV columns: {fieldnames}")
            
            address_column = find_url_column(fieldnames)
            if not address_column:
                raise ValueError(f"Could not find URL column. Available columns: {', '.join(fieldnames)}")
            
            logger.info(f"Using URL column: '{address_column}'")
            
            indexability_column = find_indexability_column(fieldnames)
            if indexability_column:
                logger.info(f"Using indexability column: '{indexability_column}'")
            
            indexable_count = 0
            skipped_count = 0
            non_indexable_count = 0
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    url = row.get(address_column, '').strip()
                    if not url:
                        continue
                    
                    if indexability_column:
                        indexability = row.get(indexability_column, '').strip()
                        indexability_lower = indexability.lower()
                        
                        if (
                            indexability_lower in ['false', 'no', 'n', '0', ''] or
                            'non' in indexability_lower or
                            'not' in indexability_lower or
                            'no index' in indexability_lower or
                            'noindex' in indexability_lower
                        ):
                            non_indexable_count += 1
                            continue
                        
                        if 'index' in indexability_lower and any(neg in indexability_lower for neg in ['non', 'not', 'no ']):
                            non_indexable_count += 1
                            continue
                    
                    parsed = urlparse(url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    
                    if base_url not in base_domains:
                        skipped_count += 1
                        continue
                    
                    path = parsed.path
                    
                    matched_homepage = None
                    for key, homepage_data in homepages.items():
                        homepage_parsed = urlparse(homepage_data['url'])
                        homepage_path = homepage_parsed.path.rstrip('/')
                        
                        if path.startswith(homepage_path):
                            matched_homepage = key
                            break
                    
                    if matched_homepage:
                        key = matched_homepage
                    else:
                        key = base_url.lower()
                    
                    path_pattern = extract_url_pattern(url, base_url)
                    
                    pages[key].append((url, path_pattern))
                    indexable_count += 1
                    
                    if row_num % 1000 == 0:
                        logger.info(f"Processed {format_number(row_num)} rows, {format_number(indexable_count)} indexable URLs")
                
                except Exception as e:
                    logger.error(f"Row {row_num}: Error parsing URL: {str(e)}")
                    continue
        
        logger.info(f"Parsing complete: {format_number(indexable_count)} indexable, {format_number(non_indexable_count)} non-indexable, {format_number(skipped_count)} skipped")
        logger.info(f"Pages grouped by locale: {dict((k, format_number(len(v))) for k, v in pages.items())}")
        
        if indexable_count == 0:
            log_error("No indexable pages found! Check your CSV format and indexability column.")
        
        return pages
        
    except Exception as e:
        log_error(f"Error parsing internal CSV: {str(e)}")
        raise

def estimate_xml_size(urlset):
    """Estimate the size of XML in bytes"""
    try:
        rough_string = tostring(urlset, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        return len(pretty_xml.encode('utf-8'))
    except:
        return 0

def generate_sitemap(homepage_url, pages, locale_key, sitemap_index=1, include_homepage=True):
    """Generate a single sitemap with URL and size limits
    
    Args:
        homepage_url: URL of the homepage (or None for master sitemaps)
        pages: List of (url, path_pattern) tuples
        locale_key: Key identifying the locale/sitemap
        sitemap_index: Index number of this sitemap
        include_homepage: Whether to include homepage in sitemap
    """
    urlset = Element('urlset', {
        'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'
    })

    url_list = []
    url_count = 0
    max_size_bytes = MAX_SITEMAP_SIZE_MB * 1024 * 1024

    # Add homepage if requested and this is the first sitemap
    if include_homepage and homepage_url and sitemap_index == 1:
        url_elem = SubElement(urlset, 'url')
        loc = SubElement(url_elem, 'loc')
        loc.text = homepage_url if homepage_url.endswith('/') else homepage_url + '/'
        
        url_list.append((homepage_url + '/', locale_key))
        url_count += 1

    added_urls = set([homepage_url + '/']) if (include_homepage and homepage_url and sitemap_index == 1) else set()

    for full_url, path in pages:
        if full_url in added_urls:
            continue
            
        if url_count >= MAX_URLS_PER_SITEMAP:
            break
            
        url_elem = SubElement(urlset, 'url')
        loc = SubElement(url_elem, 'loc')
        loc.text = full_url
        
        url_list.append((full_url, locale_key))
        
        added_urls.add(full_url)
        url_count += 1
        
        if url_count % 100 == 0:
            estimated_size = estimate_xml_size(urlset)
            if estimated_size > max_size_bytes:
                logger.warning(f"Sitemap size limit reached at {format_number(url_count)} URLs ({estimated_size / 1024 / 1024:.2f} MB)")
                break

    return urlset, url_list, url_count

def generate_sitemap_index(base_url, num_sitemaps, identifier, today, is_paginated=False):
    """Generate a sitemap index file
    
    Args:
        base_url: Base URL for the sitemap location (or None for master)
        num_sitemaps: Number of sitemaps to include
        identifier: Identifier for the sitemap files
        today: Date string
        is_paginated: Whether this is for paginated pages
    """
    sitemapindex = Element('sitemapindex', {
        'xmlns': 'http://www.sitemaps.org/schemas/sitemap/0.9'
    })
    
    prefix = "paginated_" if is_paginated else ""
    base_filename = f"{prefix}sitemap_{today}_{identifier}"
    
    for i in range(1, num_sitemaps + 1):
        sitemap_elem = SubElement(sitemapindex, 'sitemap')
        loc = SubElement(sitemap_elem, 'loc')
        
        if base_url:
            loc.text = f"{base_url}/{base_filename}_{i}.xml.gz"
        else:
            # For master sitemaps, use a placeholder
            loc.text = f"https://yourdomain.com/{base_filename}_{i}.xml.gz"
        
        lastmod = SubElement(sitemap_elem, 'lastmod')
        lastmod.text = datetime.now().strftime('%Y-%m-%d')
    
    return sitemapindex

def save_sitemap(urlset, filename, raw_filename):
    """Save sitemap to file"""
    try:
        rough_string = tostring(urlset, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        with open(raw_filename, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        with gzip.open(filename, 'wt', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        logger.info(f"Saved sitemap: {filename}")
        
    except Exception as e:
        log_error(f"Error saving sitemap {filename}: {str(e)}")
        raise

def get_uploaded_files():
    """Get list of uploaded files"""
    homepage_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('_homepage.csv')]
    internal_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('_internal.csv')]
    return homepage_files, internal_files

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            homepage_file = request.files.get('homepage_file')
            internal_file = request.files.get('internal_file')
            homepage_select = request.form.get('homepage_select')
            internal_select = request.form.get('internal_select')

            logger.info(f"Form data - homepage_select: {homepage_select}, internal_select: {internal_select}")
            logger.info(f"Files - homepage_file: {homepage_file.filename if homepage_file else 'None'}, internal_file: {internal_file.filename if internal_file else 'None'}")

            homepage_path = None
            if homepage_file and homepage_file.filename and homepage_file.filename.strip():
                homepage_filename = secure_filename(homepage_file.filename)
                homepage_filename = f"{datetime.now().strftime('%Y%m%d')}_{homepage_filename.rsplit('.', 1)[0]}_homepage.csv"
                homepage_path = os.path.join(app.config['UPLOAD_FOLDER'], homepage_filename)
                homepage_file.save(homepage_path)
                logger.info(f"Uploaded homepage file: {homepage_path}")
            elif homepage_select and homepage_select.strip():
                homepage_path = os.path.join(app.config['UPLOAD_FOLDER'], homepage_select)
                if not os.path.exists(homepage_path):
                    log_error(f"Selected homepage file does not exist: {homepage_path}")
                    return redirect(request.url)
                logger.info(f"Selected homepage file: {homepage_path}")
            
            if not homepage_path:
                log_error("No homepage file selected or uploaded")
                return redirect(request.url)

            internal_path = None
            if internal_file and internal_file.filename and internal_file.filename.strip():
                internal_filename = secure_filename(internal_file.filename)
                internal_filename = f"{datetime.now().strftime('%Y%m%d')}_{internal_filename.rsplit('.', 1)[0]}_internal.csv"
                internal_path = os.path.join(app.config['UPLOAD_FOLDER'], internal_filename)
                internal_file.save(internal_path)
                logger.info(f"Uploaded internal file: {internal_path}")
            elif internal_select and internal_select.strip():
                internal_path = os.path.join(app.config['UPLOAD_FOLDER'], internal_select)
                if not os.path.exists(internal_path):
                    log_error(f"Selected internal file does not exist: {internal_path}")
                    return redirect(request.url)
                logger.info(f"Selected internal file: {internal_path}")
            
            if not internal_path:
                log_error("No internal file selected or uploaded")
                return redirect(request.url)

            global progress
            progress = {"status": "Starting", "percentage": 0, "error": None}

            logger.info("Starting to parse homepage CSV...")
            homepages = parse_homepage_csv(homepage_path)
            
            logger.info("Starting to parse internal CSV...")
            internal_pages = parse_internal_csv(internal_path, homepages)

            today = datetime.now().strftime("%Y%m%d")
            all_urls = []
            all_urls_master = []  # For master sitemap
            all_paginated_urls = []  # For paginated pages
            skipped_locales = []

            total_homepages = len(homepages)
            logger.info(f"Generating sitemaps for {format_number(total_homepages)} locales...")
            
            # Process locale-specific sitemaps
            for i, (lang_region, homepage) in enumerate(homepages.items()):
                progress["status"] = f"Processing {lang_region}"
                progress["percentage"] = int((i / (total_homepages + 1)) * 90)  # Reserve 10% for master
                logger.info(f"Processing {lang_region} ({i+1}/{total_homepages})")

                pages = internal_pages.get(lang_region, [])
                logger.info(f"Found {format_number(len(pages))} pages for {lang_region}")
                
                if not pages:
                    logger.warning(f"No pages found for {lang_region}, skipping sitemap generation")
                    skipped_locales.append({
                        'locale': lang_region,
                        'homepage': homepage['url'],
                        'section': homepage.get('section', ''),
                        'country': homepage['country']
                    })
                    continue
                
                # Separate paginated from regular pages
                regular_pages = []
                paginated_pages = []
                
                for url, path in pages:
                    if is_paginated_url(url):
                        paginated_pages.append((url, path))
                    else:
                        regular_pages.append((url, path))
                
                logger.info(f"{lang_region}: {format_number(len(regular_pages))} regular, {format_number(len(paginated_pages))} paginated")
                
                section = homepage.get('section', '')
                country = homepage.get('country', '').upper()
                locale_key = f"{section}_{country}" if section else lang_region.upper()
                
                # Generate regular sitemaps
                if regular_pages:
                    sitemap_number = 1
                    remaining_pages = regular_pages
                    
                    while True:
                        pages_to_process = remaining_pages
                        
                        urlset, url_list, url_count = generate_sitemap(
                            homepage['url'], pages_to_process, locale_key, sitemap_number, include_homepage=True
                        )
                        all_urls.extend(url_list)
                        all_urls_master.extend(url_list)  # Add to master list
                        
                        if len(regular_pages) > MAX_URLS_PER_SITEMAP or sitemap_number > 1:
                            filename = os.path.join(OUTPUT_FOLDER, f"sitemap_{today}_{locale_key}_{sitemap_number}.xml.gz")
                            raw_filename = os.path.join(RAW_OUTPUT_FOLDER, f"sitemap_{today}_{locale_key}_{sitemap_number}.xml")
                        else:
                            filename = os.path.join(OUTPUT_FOLDER, f"sitemap_{today}_{locale_key}.xml.gz")
                            raw_filename = os.path.join(RAW_OUTPUT_FOLDER, f"sitemap_{today}_{locale_key}.xml")
                        
                        save_sitemap(urlset, filename, raw_filename)
                        
                        if sitemap_number == 1 and url_count > 1:
                            remaining_pages = remaining_pages[url_count-1:]
                        else:
                            remaining_pages = remaining_pages[url_count:]
                        
                        if not remaining_pages or url_count == 0:
                            break
                        
                        sitemap_number += 1
                        
                        if sitemap_number > 100:
                            logger.warning(f"Reached maximum sitemap limit for {lang_region}")
                            break
                    
                    # Generate sitemap index if needed
                    if sitemap_number > 1:
                        logger.info(f"Generating sitemap index for {lang_region} ({sitemap_number} sitemaps)")
                        sitemap_index = generate_sitemap_index(homepage['url'], sitemap_number, locale_key, today)
                        index_filename = os.path.join(OUTPUT_FOLDER, f"sitemap_index_{today}_{locale_key}.xml.gz")
                        index_raw_filename = os.path.join(RAW_OUTPUT_FOLDER, f"sitemap_index_{today}_{locale_key}.xml")
                        save_sitemap(sitemap_index, index_filename, index_raw_filename)
                
                # Generate paginated sitemaps
                if paginated_pages:
                    sitemap_number = 1
                    remaining_pages = paginated_pages
                    
                    while True:
                        pages_to_process = remaining_pages
                        
                        urlset, url_list, url_count = generate_sitemap(
                            None, pages_to_process, f"{locale_key}_paginated", sitemap_number, include_homepage=False
                        )
                        all_paginated_urls.extend(url_list)
                        
                        if len(paginated_pages) > MAX_URLS_PER_SITEMAP or sitemap_number > 1:
                            filename = os.path.join(PAGINATED_OUTPUT_FOLDER, f"paginated_sitemap_{today}_{locale_key}_{sitemap_number}.xml.gz")
                            raw_filename = os.path.join(PAGINATED_RAW_OUTPUT_FOLDER, f"paginated_sitemap_{today}_{locale_key}_{sitemap_number}.xml")
                        else:
                            filename = os.path.join(PAGINATED_OUTPUT_FOLDER, f"paginated_sitemap_{today}_{locale_key}.xml.gz")
                            raw_filename = os.path.join(PAGINATED_RAW_OUTPUT_FOLDER, f"paginated_sitemap_{today}_{locale_key}.xml")
                        
                        save_sitemap(urlset, filename, raw_filename)
                        
                        remaining_pages = remaining_pages[url_count:]
                        
                        if not remaining_pages or url_count == 0:
                            break
                        
                        sitemap_number += 1
                        
                        if sitemap_number > 100:
                            logger.warning(f"Reached maximum paginated sitemap limit for {lang_region}")
                            break
                    
                    # Generate paginated sitemap index if needed
                    if sitemap_number > 1:
                        logger.info(f"Generating paginated sitemap index for {lang_region} ({sitemap_number} sitemaps)")
                        sitemap_index = generate_sitemap_index(None, sitemap_number, locale_key, today, is_paginated=True)
                        index_filename = os.path.join(PAGINATED_OUTPUT_FOLDER, f"paginated_sitemap_index_{today}_{locale_key}.xml.gz")
                        index_raw_filename = os.path.join(PAGINATED_RAW_OUTPUT_FOLDER, f"paginated_sitemap_index_{today}_{locale_key}.xml")
                        save_sitemap(sitemap_index, index_filename, index_raw_filename)

            # Generate MASTER sitemaps (all URLs combined, excluding paginated)
            progress["status"] = "Generating master sitemaps"
            progress["percentage"] = 90
            logger.info(f"Generating master sitemaps with {format_number(len(all_urls_master))} total URLs...")
            
            # Convert master list to required format
            master_pages = [(url, '') for url, _ in all_urls_master]
            
            sitemap_number = 1
            remaining_pages = master_pages
            total_master_sitemaps = 0
            
            while remaining_pages:
                pages_to_process = remaining_pages
                
                urlset, _, url_count = generate_sitemap(
                    None, pages_to_process, "master", sitemap_number, include_homepage=False
                )
                
                if len(master_pages) > MAX_URLS_PER_SITEMAP or sitemap_number > 1:
                    filename = os.path.join(MASTER_OUTPUT_FOLDER, f"master_sitemap_{today}_{sitemap_number}.xml.gz")
                    raw_filename = os.path.join(MASTER_RAW_OUTPUT_FOLDER, f"master_sitemap_{today}_{sitemap_number}.xml")
                else:
                    filename = os.path.join(MASTER_OUTPUT_FOLDER, f"master_sitemap_{today}.xml.gz")
                    raw_filename = os.path.join(MASTER_RAW_OUTPUT_FOLDER, f"master_sitemap_{today}.xml")
                
                save_sitemap(urlset, filename, raw_filename)
                total_master_sitemaps = sitemap_number
                
                remaining_pages = remaining_pages[url_count:]
                
                if not remaining_pages or url_count == 0:
                    break
                
                sitemap_number += 1
                
                if sitemap_number > 100:
                    logger.warning("Reached maximum master sitemap limit")
                    break
            
            # Generate master sitemap index if needed
            if total_master_sitemaps > 1:
                logger.info(f"Generating master sitemap index ({total_master_sitemaps} sitemaps)")
                master_index = generate_sitemap_index(None, total_master_sitemaps, "master", today)
                index_filename = os.path.join(MASTER_OUTPUT_FOLDER, f"master_sitemap_index_{today}.xml.gz")
                index_raw_filename = os.path.join(MASTER_RAW_OUTPUT_FOLDER, f"master_sitemap_index_{today}.xml")
                save_sitemap(master_index, index_filename, index_raw_filename)

            # Save CSV reports
            csv_filename = f"all_urls_{today}.csv"
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['URL', 'Sitemap'])
                writer.writerows(all_urls)
            logger.info(f"Generated CSV with {format_number(len(all_urls))} URLs")

            if all_paginated_urls:
                paginated_csv_filename = f"all_paginated_urls_{today}.csv"
                with open(paginated_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['URL', 'Sitemap'])
                    writer.writerows(all_paginated_urls)
                logger.info(f"Generated paginated CSV with {format_number(len(all_paginated_urls))} URLs")

            if skipped_locales:
                skipped_report_filename = f"skipped_locales_{today}.csv"
                with open(skipped_report_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=['locale', 'homepage', 'section', 'country'])
                    writer.writeheader()
                    writer.writerows(skipped_locales)
                logger.info(f"Generated skipped locales report: {skipped_report_filename}")

            progress["status"] = "Complete"
            progress["percentage"] = 100
            logger.info("="*60)
            logger.info("SITEMAP GENERATION COMPLETE!")
            logger.info(f"Regular URLs: {format_number(len(all_urls))}")
            logger.info(f"Paginated URLs: {format_number(len(all_paginated_urls))}")
            logger.info(f"Master Sitemaps: {total_master_sitemaps}")
            logger.info("="*60)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            log_error(error_msg)
            logger.exception("Full error traceback:")
            progress["status"] = "Error"
            progress["error"] = error_msg
            progress["percentage"] = 0

        return redirect(url_for('success'))

    homepage_files, internal_files = get_uploaded_files()
    return render_template('index.html', homepage_files=homepage_files, internal_files=internal_files)

@app.route('/progress')
def get_progress():
    return jsonify(progress)

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/download_compressed')
def download_compressed():
    return create_zip_file(OUTPUT_FOLDER, 'locale_sitemaps_compressed.zip')

@app.route('/download_raw')
def download_raw():
    return create_zip_file(RAW_OUTPUT_FOLDER, 'locale_sitemaps_raw.zip')

@app.route('/download_master_compressed')
def download_master_compressed():
    return create_zip_file(MASTER_OUTPUT_FOLDER, 'master_sitemaps_compressed.zip')

@app.route('/download_master_raw')
def download_master_raw():
    return create_zip_file(MASTER_RAW_OUTPUT_FOLDER, 'master_sitemaps_raw.zip')

@app.route('/download_paginated_compressed')
def download_paginated_compressed():
    return create_zip_file(PAGINATED_OUTPUT_FOLDER, 'paginated_sitemaps_compressed.zip')

@app.route('/download_paginated_raw')
def download_paginated_raw():
    return create_zip_file(PAGINATED_RAW_OUTPUT_FOLDER, 'paginated_sitemaps_raw.zip')

@app.route('/download_csv')
def download_csv():
    today = datetime.now().strftime("%Y%m%d")
    csv_filename = f"all_urls_{today}.csv"
    return send_file(
        csv_filename,
        download_name=csv_filename,
        as_attachment=True,
        mimetype='text/csv'
    )

@app.route('/download_paginated_csv')
def download_paginated_csv():
    today = datetime.now().strftime("%Y%m%d")
    csv_filename = f"all_paginated_urls_{today}.csv"
    if os.path.exists(csv_filename):
        return send_file(
            csv_filename,
            download_name=csv_filename,
            as_attachment=True,
            mimetype='text/csv'
        )
    else:
        return "No paginated URLs file found", 404

@app.route('/download_skipped')
def download_skipped():
    today = datetime.now().strftime("%Y%m%d")
    skipped_filename = f"skipped_locales_{today}.csv"
    if os.path.exists(skipped_filename):
        return send_file(
            skipped_filename,
            download_name=skipped_filename,
            as_attachment=True,
            mimetype='text/csv'
        )
    else:
        return "No skipped locales file found", 404

def create_zip_file(source_folder, zip_filename):
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                zf.write(os.path.join(root, file), file)
    memory_file.seek(0)
    return send_file(
        memory_file,
        download_name=zip_filename,
        as_attachment=True,
        mimetype='application/zip'
    )

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Enhanced Sitemap Generator Starting!")
    print("="*60)
    print(f"📂 Upload folder: {UPLOAD_FOLDER}")
    print(f"📝 Output folders:")
    print(f"   - Locale sitemaps: {OUTPUT_FOLDER}")
    print(f"   - Master sitemaps: {MASTER_OUTPUT_FOLDER}")
    print(f"   - Paginated sitemaps: {PAGINATED_OUTPUT_FOLDER}")
    print(f"🌐 Open your browser to: http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)