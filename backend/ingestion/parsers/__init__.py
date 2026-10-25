from ingestion.parsers.bank_accounts import (
    try_parse_chase,
    try_parse_hdfc,
    try_parse_icici,
    try_parse_kotak,
    try_parse_standard_chartered,
)
from ingestion.parsers.brokerage import try_parse_fidelity, try_parse_morgan_stanley_rsu
from ingestion.parsers.demat import try_parse_cdsl_consolidated_demat_cas, try_parse_demat_cas
from ingestion.parsers.deposits import try_parse_fd, try_parse_fd_summary, try_parse_rd
from ingestion.parsers.insurance import try_parse_term_insurance, try_parse_ulip
from ingestion.parsers.loans import try_parse_loan_statement
from ingestion.parsers.mutual_funds import (
    try_parse_cams_cas,
    try_parse_cams_kfintech_summary,
    try_parse_cdsl_mutual_fund_cas,
    try_parse_navi_account_statement,
    try_parse_standalone_amc_statement,
)
from ingestion.parsers.retirement import try_parse_epf, try_parse_nps
from ingestion.parsers.sgb import try_parse_sgb_confirmation

# Tried in order; each function checks its own distinctive markers and returns None
# if they're absent, so ordering mostly doesn't affect correctness — it's set here
# roughly by expected frequency, cheapest/most distinctive checks first.
PARSERS = [
    try_parse_hdfc,
    try_parse_icici,
    try_parse_chase,
    try_parse_kotak,
    try_parse_standard_chartered,
    try_parse_loan_statement,
    try_parse_fd,
    try_parse_fd_summary,
    try_parse_rd,
    try_parse_cams_cas,
    try_parse_cams_kfintech_summary,
    try_parse_cdsl_mutual_fund_cas,
    try_parse_navi_account_statement,
    try_parse_standalone_amc_statement,
    try_parse_demat_cas,
    try_parse_cdsl_consolidated_demat_cas,
    try_parse_epf,
    try_parse_nps,
    try_parse_sgb_confirmation,
    try_parse_ulip,
    try_parse_term_insurance,
    try_parse_morgan_stanley_rsu,
    try_parse_fidelity,
]
