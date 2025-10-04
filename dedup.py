import pandas as pd
import difflib
import os
from datetime import datetime

# Normalize functions
def normalize_string(s):
    if pd.isna(s):
        return ''
    return str(s).lower().strip().replace('"', '').replace(',', '')

def normalize_phone(p):
    if pd.isna(p):
        return ''
    p = str(p).strip()
    # Strip extension (e.g., remove 'x72224')
    if 'x' in p:
        p = p.split('x')[0].strip()
    return ''.join(c for c in p if c.isdigit() or c == '+')

def normalize_website(w):
    if pd.isna(w):
        return ''
    w = str(w).lower().replace('www.', '').replace('http://', '').replace('https://', '').rstrip('/')
    return w

# Format phone for HubSpot (E.164: +country digits only, validate length)
def format_hubspot_phone(p):
    if pd.isna(p):
        return ''
    p = normalize_phone(p)
    digits_plus = ''.join(c for c in p if c.isdigit() or c == '+')
    if not digits_plus:
        return ''
    if '+' not in digits_plus:
        # Assume US: prepend +1 for 10 digits
        if len(digits_plus) == 10:
            digits_plus = '+1' + digits_plus
        elif len(digits_plus) == 11 and digits_plus.startswith('1'):
            digits_plus = '+' + digits_plus
        else:
            digits_plus = '+' + digits_plus  # Fallback
    # Validate: + followed by digits, total 10-15 digits
    total_digits = len(''.join(c for c in digits_plus if c.isdigit()))
    if digits_plus.startswith('+') and 10 <= total_digits <= 15:
        return digits_plus
    else:
        return ''  # Invalid: output empty to avoid errors

# Similarity score
def similarity_score(row1, row2):
    fields = ['Business Name', 'Address', 'Phone Number', 'Website']
    weights = [0.4, 0.3, 0.2, 0.1]
    score = 0.0
    total_weight = 0.0
    for field, weight in zip(fields, weights):
        val1 = row1.get(field, '')
        val2 = row2.get(field, '')
        if val1 and val2:
            if field in ['Phone Number', 'Website']:
                sim = 1.0 if val1 == val2 else difflib.SequenceMatcher(None, val1, val2).ratio()
            else:
                sim = difflib.SequenceMatcher(None, val1, val2).ratio()
            score += sim * weight
            total_weight += weight
        elif val1 or val2:
            total_weight += weight / 2
    return score / total_weight if total_weight > 0 else 0.0


def main():
    # Fixed paths
    master_path = r"C:\Users\ADMIN\python projects\Deduplication_project\master_list.csv"
    new_path = r"C:\Users\ADMIN\python projects\Deduplication_project\new_scraped_data.csv"
    output_dir = r"C:\Users\ADMIN\python projects\Deduplication_project\results"

    dupe_threshold = 0.85
    possible_threshold = 0.7

    # Load data (CSV or Excel)
    def load_df(path):
        if path.endswith('.xlsx'):
            return pd.read_excel(path)
        else:
            return pd.read_csv(path, quotechar='"', escapechar='\\')

    master_df = load_df(master_path)
    new_df = load_df(new_path)

    # Normalize key fields (for matching only; output formatting separate)
    cols = ['Business Name', 'Address', 'Website']
    for df in [master_df, new_df]:
        for col in cols:
            if col in df.columns:
                df[col] = df[col].apply(normalize_string)
        if 'Phone Number' in df.columns:
            df['Phone Number'] = df['Phone Number'].apply(normalize_phone)
        if 'Website' in df.columns:
            df['Website'] = df['Website'].apply(normalize_website)

    # Deduplication
    duplicates, possibles, uniques = [], [], []
    for idx, new_row in new_df.iterrows():
        max_score = 0.0
        match_row = None
        for _, master_row in master_df.iterrows():
            sc = similarity_score(new_row, master_row)
            if sc > max_score:
                max_score = sc
                match_row = master_row
        if max_score >= dupe_threshold:
            duplicates.append((new_row, match_row, max_score))
        elif max_score >= possible_threshold:
            possibles.append((new_row, match_row, max_score))
        else:
            uniques.append(new_row)

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Updated master with uniques appended (normalized phones, no forced + formatting)
    if uniques:
        new_uniques_df = pd.DataFrame(uniques)
        all_cols = list(set(master_df.columns) | set(new_uniques_df.columns))
        master_df = master_df.reindex(columns=all_cols)
        new_uniques_df = new_uniques_df.reindex(columns=all_cols)
        updated_master = pd.concat([master_df, new_uniques_df], ignore_index=True)
        
        # No phone formatting here to avoid interference; keep normalized
        if 'Phone Number' in updated_master.columns:
            updated_master['Phone Number'] = updated_master['Phone Number'].astype(str)
        
        updated_path = os.path.join(output_dir, f'updated_master_{timestamp}.xlsx')
        updated_master.to_excel(updated_path, index=False)
    else:
        updated_path = master_path

    # HubSpot-ready CSV of new uniques (formatted and validated phones with +)
    hubspot_path = os.path.join(output_dir, f'hubspot_ready_new_uniques_{timestamp}.csv') if uniques else None
    if hubspot_path:
        # Copy for HubSpot-specific formatting
        hubspot_df = new_uniques_df.copy()
        # Format and validate phones with + for HubSpot
        hubspot_df['Phone Number'] = hubspot_df['Phone Number'].apply(format_hubspot_phone)
        if 'Phone Number' in hubspot_df.columns:
            hubspot_df['Phone Number'] = hubspot_df['Phone Number'].astype(str)
        hubspot_df.to_csv(hubspot_path, index=False)

    # Possibles CSV (no phone formatting needed, as it's for review)
    possibles_path = os.path.join(output_dir, f'possibles_{timestamp}.csv') if possibles else None
    if possibles_path:
        possibles_df = pd.DataFrame([
            {'New_' + k: v for k, v in p[0].items()} |
            {'Master_' + k: v for k, v in p[1].items()} |
            {'Score': p[2]} for p in possibles
        ])
        possibles_df.to_csv(possibles_path, index=False)

    # Log file (include invalid phone count)
    invalid_phones = sum(1 for row in new_df.itertuples() if hasattr(row, 'Phone_Number') and not format_hubspot_phone(row.Phone_Number))
    log_path = os.path.join(output_dir, f'report_{timestamp}.txt')
    with open(log_path, 'w') as log:
        log.write(f"Run at: {timestamp}\nMaster rows: {len(master_df)}\nNew rows: {len(new_df)}\n")
        log.write(f"Invalid phones skipped: {invalid_phones}\n")
        log.write(f"Duplicates: {len(duplicates)}\n")
        for new, mast, sc in duplicates:
            log.write(f"Score: {sc:.2f}\nNew: {new.to_dict()}\nMaster: {mast.to_dict()}\n\n")
        log.write(f"Possibles: {len(possibles)}\n")
        for new, mast, sc in possibles:
            log.write(f"Score: {sc:.2f}\nNew: {new.to_dict()}\nMaster: {mast.to_dict()}\n\n")
        log.write(f"Uniques added: {len(uniques)}\nUpdated master: {updated_path}\nHubSpot-ready CSV: {hubspot_path or 'None'}\nPossibles CSV: {possibles_path or 'None'}\n")

    print(f"✅ Deduplication complete. Invalid phones skipped: {invalid_phones}.\nOutputs saved in: {output_dir}")


if __name__ == "__main__":
    main()