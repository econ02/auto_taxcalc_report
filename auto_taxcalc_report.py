import re
import os
import sys
import math
import copy
import locale
import datetime
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from taxcalc import *
from decimal import *
from pylatex.utils import italic, NoEscape
from pylatex.base_classes import Container, Command
from pylatex import Document, PageStyle, Head, Foot, MiniPage, Section, \
                    Command, StandAloneGraphic, MultiColumn, MultiRow, Tabu, \
                    LongTabu, LargeText, MediumText, LineBreak, NewPage, \
                    Tabularx, Tabular, TextColor, simple_page_number, Figure, \
                    Subsection, Math, TikZ, Axis, Plot, Figure, Matrix, Itemize


table_vars_dict = dict([("10-Year Revenue Change (billions)",
                         "currency_fmt(ten_year_cost_PE(calc_cl, calc_dict[key1][key2], beh_dict[key2]))"),
                        ("10-Year Revenue Change (billions)",
                         "currency_fmt(ten_year_cost(calc_cl, calc_dict[key1][key2]))"),
                        ("Deduction Cap, Joint Filers",
                         "double(key1)"),
                        ("Itemizers (millions)",
                         "'{:,.1f}'.format(num_ided(calc_dict[key1][key2]) / 10.0**6)"),
                        ("Taxpayers Facing Lower Marginal Tax Rate (millions)",
                         "'{:,.1f}'.format(lwrMTR_wages(calc_cl, calc_dict[key1][key2]) / 10.0**6)"),
                        ("Taxpayers Paying Zero or Less Income Tax (millions)",
                         "'{:,.1f}'.format(no_inc_tax(calc_dict[key1][key2]) / 10.0**6)"),
                        ("Taxpayers Receiving Tax Cut (millions)",
                         "'{:,.1f}'.format(num_taxcut(calc_cl, calc_dict[key1][key2]) / 10.0**6)"),
                        ("Taxpayers Receiving Tax Hike (millions)",
                         "'{:,.1f}'.format(num_taxhike(calc_cl, calc_dict[key1][key2]) / 10.0**6)"),
                        ("Total Charitable Contributions (billions)",
                         "currency_fmt(num_charity(calc_dict[key1][key2]))"),
                        ("Wght. Ave. MTR on Charitable Contributions",
                         "'{:.2f}'.format(100 * charity_wmtr(calc_cl))"),
                        ("Reform",
                         "'key1'"),
                        ("Behavior",
                         "'key2'")])


def make_baseline(start_year, records_url):
    """
    Generates a baseline calculator using current law.
    """
    policy_cl = Policy()
    behavior_cl = Behavior()
    records_cl = Records(records_url)
    calc_cl = Calculator(policy_cl, records_cl, behavior_cl)
    for i in range(start_year - 2013):
        calc_cl.increment_year()
    assert calc_cl.current_year == start_year
    calc_cl.calc_all()
    return(calc_cl)


def make_calculator(calc_cl, ref_dict, start_year, beh_dict, records_url):
    """
    Makes a calculator, implimenting each behavioral reform in beh_dict.
    """
    policy1 = Policy()
    behavior1 = Behavior()
    records1 = Records(records_url)
    policy1.implement_reform(ref_dict)
    calc1 = Calculator(records=records1, policy=policy1, behavior=behavior1)
    for i in range(start_year - 2013):
        calc1.increment_year()
    assert calc1.current_year == start_year
    calc1.calc_all()
    global calc_beh_dict
    calc_beh_dict = beh_dict.copy()
    for key in beh_dict:
        behavior1.update_behavior(beh_dict[key])
        calc_beh_dict[key] = Behavior.response(calc_cl, calc1)
    return(calc_beh_dict)


def dict_calculator(ref_dict, start_year, beh_dict, records_url):
    """
    Generate a dictionary of calculators for all policy reforms,
    across all behavirors.
    """
    global calc_dict
    calc_dict = ref_dict.copy()
    for key in ref_dict:
        calc_dict[key] = make_calculator(make_baseline(start_year,
                                                       records_url),
                                         ref_dict[key],
                                         start_year,
                                         beh_dict,
                                         records_url)
    return(calc_dict)
    print('Done')


def num_charity(calc1):
    """
    Calculate the number of individuals making charitable contributions.
    """
    num = ((calc1.records.s006 * calc1.records.c19700).sum() / 10**9)
    return(num)


def ten_year_cost(calc_base, calc_ref):
    """
    Calculate the ten-year-cost of thereform without behavorial dynamics.
    """
    path = [0] * 10
    calc1 = copy.deepcopy(calc_base)
    calc2 = copy.deepcopy(calc_ref)
    for i in range(10):
        calc1.calc_all()
        calc2.calc_all()
        calc1_combined = (calc1.records.combined * calc1.records.s006)
        calc2_combined = (calc2.records.combined * calc2.records.s006)
        path[i] = (calc2_combined - calc1_combined).sum() / 10**9
        if calc1.current_year < 2026:
            calc1.increment_year()
            calc2.increment_year()
    return sum(path)


def dict_ten_year_cost(calc_dict, calc_cl):
    """
    Calculate a dictionary of ten-year-costs without behavorial dynamics.
    """
    global cost_dict
    cost_dict = copy.deepcopy(calc_dict)
    for key in calc_dict:
        key1 = key
        for key in calc_dict[key1]:
            key2 = key
            cost_dict[key1][key2] = ten_year_cost(calc_cl,
                                                  cost_dict[key1][key2])
            print(cost_dict[key1][key2])
    print('Done')


def ten_year_cost_PE(calc_base, calc_ref, tyc_beh):
    """
    Calculate the ten year cost with behavioral dynamics.
    """
    path = [0] * 10
    calc1 = copy.deepcopy(calc_base)
    calc2 = copy.deepcopy(calc_ref)
    calc2.behavior.update_behavior(tyc_beh)
    calc2b = Behavior.response(calc1, calc2)
    for i in range(10):
        calc1_combined = (calc1.records.combined * calc1.records.s006)
        calc2b_combined = (calc2b.records.combined * calc2b.records.s006)
        path[i] = (calc2b_combined - calc1_combined).sum() / 10**9
        if calc1.current_year < 2026:
            calc1.increment_year()
            calc2b.increment_year()
            calc1.calc_all()
            calc2b.calc_all()
    return sum(path)


def dict_ten_year_cost_PE(calc_cl, tyc_beh, calc_dict):
    """
    Calculate a dictionary with the ten-year-costs with behavioral dynamics.
    """
    global cost_PE_dict
    cost_PE_dict = copy.deepcopy(calc_dict)
    for key in calc_dict:
        key1 = key
        for key in calc_dict[key1]:
            key2 = key
            cost_PE_dict[key1][key2] = ten_year_cost_PE(calc_cl,
                                                        calc_dict[key1][key2],
                                                        tyc_beh)
            print(cost_PE_dict[key1][key2])
    print('Done')


def charity_wmtr(calc1):
    """
    Calculates the weighted average marginal tax rate
    for charitable contributions.
    ----------
    calc1 : calculator object
        The calculator object for which you want to
        calculate the weighted average marginal tax rate.
    """
    wgt1 = (calc1.records.e19800 * calc1.records.s006)
    wgt2 = (calc1.records.e20100 * calc1.records.s006)

    mtr1 = calc1.mtr('e19800')[2]
    mtr2 = calc1.mtr('e20100')[2]

    wmtr = sum((mtr1 * wgt1) + (mtr2 * wgt2)) / sum(wgt1 + wgt2)
    return(wmtr)


def num_ided(calc):
    """
    Calculate the number of itemizers.
    """
    ided = (calc.records.s006[(calc.records.c04470 > 0.) *
            (calc.records.c00100 > 0.)].sum())
    return(ided)


def num_std(calc):
    """
    Calculate the number of non-itemizers.
    """
    std = (calc.records.s006[(calc.records.standard > 0.) *
           (calc.records.c00100 > 0.)].sum())
    return(std)


def no_inc_tax(calc):
    """
    Calculate the number paying zero or less in income tax.
    """
    count = calc.records.s006[calc.records.iitax < 0.0001].sum()
    return(count)


def wavgMTR_wages(calc):
    mtr = ((calc.mtr('e00200p')[2] *
            calc.records.e00200 *
            calc.records.s006).sum() /
           (calc.records.e00200 * calc.records.s006).sum())
    return(mtr)


def wavgMTR_ltcg(calc):
    tgain = np.maximum(0.,
                       np.minimum(calc.records.c23650,
                                  calc.records.p23250)) + calc.records.e01100
    mtr = ((calc.mtr('p23250')[2] * tgain * calc.records.s006).sum() /
           (tgain * calc.records.s006).sum())
    return(mtr)


def wavgMTR_stcg(calc):
    tgain = np.maximum(0.,
                       np.minimum(calc.records.c23650,
                                  calc.records.p22250)) + calc.records.e01100
    mtr = ((calc.mtr('p22250')[2] * tgain * calc.records.s006).sum() /
           (tgain * calc.records.s006).sum())
    return(mtr)


def wavgMTR_int(calc):
    mtr = ((calc.mtr('e00300')[2] *
            calc.records.e00300 *
            calc.records.s006).sum() /
           (calc.records.e00300 * calc.records.s006).sum())
    return(mtr)


def wavgMTR_qdiv(calc):
    mtr = ((calc.mtr('e00650')[2] *
            calc.records.e00650 *
            calc.records.s006).sum() /
           (calc.records.e00650 * calc.records.s006).sum())
    return(mtr)


def lwrMTR_wages(calc1, calc2):
    """
    Calculate the number with a lower marginal tax rate on wages.
    ----------
    calc1 : baseline
    calc2 : reform
    """
    diff = (calc2.records.s006[(calc2.mtr('e00200p')[2] <
            calc1.mtr('e00200p')[2])].sum())
    return(diff)


def hgrMTR_wages(calc1, calc2):
    """
    Calculate the number with a higher marginal tax rate on wages.
    ----------
    calc1 : baseline
    calc2 : reform
    """
    diff = (calc2.records.s006[(calc2.mtr('e00200p')[2] >
            calc1.mtr('e00200p')[2])].sum())
    return(diff)


def num_taxcut(calc1, calc2):
    """
    Calculate the number receiving a tax cut.
    ----------
    calc1 : baseline
    calc2 : reform
    """
    diff = (calc2.records.s006[calc1.records.combined >
            calc2.records.combined].sum())
    return(diff)


def num_taxhike(calc1, calc2):
    """
    Calculate the number receiving a tax hike.
    ----------
    calc1 : baseline
    calc2 : reform
    """
    diff = (calc2.records.s006[calc1.records.combined <
            calc2.records.combined].sum())
    return(diff)


def currency_fmt(num):
    """
    Formats 'num' with dollar sign and one decimal.
    If 'num' is negative, the number and sign is placed in parenthesis.
    ----------
    num : float
        The number you are trying to format.
        If value is not a float, it will try to convert it or return an error.
    """
    num = float(num)
    if num > 0:
        return('${:,.1f}'.format(num))
    if num < 0:
        return('(${:,.1f})'.format(abs(num)))
    if num == 0:
        return('${:,.1f}'.format(num))


def verb(n):
    """
    Returns 'decrease' if the value is negative and 'increase' if positive.
    """
    n = float(n)
    if n < 0:
        return('decrease')
    if n > 0:
        return('increase')
    if n == 0:
        return('cause no change')


def header(doc):
    """
    Generate the header using PyLaTex.
    """

    doc.append(NoEscape(r'\noindent'))
#     doc.append(NoEscape(r'\begin{spacing}{2.00}'))
    doc.append(NoEscape(r'\begin{tikzpicture}[remember picture, overlay]'))
    doc.append(NoEscape(r'\node[anchor = north west, inner sep = 0.25in] at ($(current page.north west) + (0.90in, -0.30in)$)'))
    doc.append(NoEscape(r'{\includegraphics[width=85px]{aei_logo2.jpg}};'))
    doc.append(NoEscape(r'\end{tikzpicture}'))
    doc.append(NoEscape(r'\noindent'))
    doc.append(NoEscape(r'\\'))
    doc.append(NoEscape(r'\\'))
    doc.append(NoEscape(r'Powered by Open Source Policy Modeling\\'))
    doc.append(NoEscape(r'\\'))
    doc.append(paper_title)
    doc.append(NoEscape(r'\\'))
    doc.append(paper_byline)


def add_packages(doc):
    """
    Add packages to the LaTeX file.
    """
    doc.preamble.append(Command('usepackage', 'xcolor'))
    doc.preamble.append(Command('usepackage', 'hyperref'))
    doc.preamble.append(Command('usepackage', 'xcolor'))
    doc.preamble.append(Command('usepackage', 'enumitem'))
    doc.preamble.append(Command('usepackage', 'titling'))
    doc.preamble.append(Command('usepackage', 'graphicx'))
    doc.preamble.append(Command('usepackage', 'sectsty'))
    doc.preamble.append(Command('usepackage', 'titlesec'))
    doc.preamble.append(Command('usepackage', 'setspace'))
    doc.preamble.append(Command('usepackage', 'tikz'))
    doc.preamble.append(Command('usepackage', 'calc'))
    doc.preamble.append(Command('usetikzlibrary', 'calc'))
    doc.preamble.append(Command('renewcommand', NoEscape(r'\rmdefault}{phv')))
    doc.preamble.append(Command('renewcommand', NoEscape(r'\sfdefault}{phv')))
    doc.preamble.append(Command('sectionfont', NoEscape(r'\fontsize{12}{15}\selectfont')))
    doc.preamble.append(Command('titlespacing*', NoEscape(r'\section}{0pt}{0.5\baselineskip}{0.5\baselineskip')))


def policy(doc):
    """
    Create a 'Current Policy' section using the policy_string.
    """
    with doc.create(Section('Current Policy', numbers=True)):
        doc.append(policy_string)


def options(doc):
    """
    Create a "Reform options" section using the options_string.
    """
    with doc.create(Section('Reform Options', numbers=True)):
        doc.append(options_string)


def comments(doc):
    """
    Add comments (bullet points).
    """
    with doc.create(Section('Comments', numbers=True)):
        with doc.create(Itemize()) as itemize:
            itemize.add_item(bullet_1)
            itemize.add_item(bullet_2)
            itemize.add_item(bullet_3)
            itemize.add_item(bullet_4)


def auto_bullets(doc, ref_dict=ref_dict):
    """
    Generate automate bullets using ref_dict.
    """
    global bullets_std
    bullets_std = []
    for key in ref_dict:
        str1 = (key + " causes " +
                str('{:.1f} million'.format(hgrMTR_wages(calc_cl, calc_dict[key][baseline_behavior_name]) / 10.0**6)) +
                " people to face higher marginal tax rates on labor income and " +
                str('{:.1f} million'.format(lwrMTR_wages(calc_cl, calc_dict[key][baseline_behavior_name]) / 10.0**6)) +
                " people to face lower marginal tax rates.")
        if key != "Current Law":
            bullets_std.append(str1)
    return(bullets_std)


def auto_comments(doc):
    """
    Loop through bullets_std and add them to list.
    """
    with doc.create(Section('Comments', numbers=True)):
        with doc.create(Itemize()) as itemize:
            for s in bullets_std:
                itemize.add_item(s)
            for s in bullets_nstd:
                itemize.add_item(s)


def comments(doc):
    """
    Add comments (bullet points).
    """
    with doc.create(Section('Comments', numbers=True)):
        with doc.create(Itemize()) as itemize:
            for bullet in bullet_list:
                itemize.add_item(bullet)


def double(key1):
    if key1 == 'Current Law':
        return('Current Law')
    else:
        return('${:,.0f}'.format(2 * float(re.sub("[^\d\.]", "", (key1)))))


def v_table(doc, policy_key=True):
    """
    Creates a vertical table, with reforms on y-axis and metrics on x-axis
    ----------
    policy_key : This determines the listing on the y-axis, By default it is set
    so that key1=True.
        policy_key = True : Uses policy reforms
        policy_key = False : Uses behavioral reforms
    """
    with doc.create(LongTabu("X[c] X[c] X[c] X[c] X[c] X[c]", row_height=2.0)) as data_table:
        data_table.add_hline()
        data_table.add_row(['Elasticity of Charitable Giving',
                            'Taxpayers Receiving Tax Hike (millions)',
                            'Itemizers (millions)',
                            'Wght. Ave. MTR on Charitable Contributions',
                            'Total Charitable Contributions (billions)',
                            '10-Year Revenue Change (billions)'])
        data_table.add_hline()
        for key in calc_dict:
            key1 = key
            for key in calc_dict[key]:
                key2 = key
                if policy_key == True:
                    data_table.add_row([key1,
                                       '{:,.1f}'.format(num_taxhike(calc_cl, calc_dict[key1][key2]) / 10.0**6),
                                       '{:,.1f}'.format(num_ided(calc_dict[key1][key2]) / 10.0**6),
                                       '{:.2f}'.format(100 * charity_wmtr(calc_cl)),
                                       currency_fmt(num_charity(calc_dict[key1][key2])),
                                       currency_fmt(ten_year_cost(calc_cl, calc_dict[key1][key2]))])
                if policy_key == False:
                    data_table.add_row([key2,
                                       '{:,.1f}'.format(num_taxhike(calc_cl, calc_dict[key1][key2]) / 10.0**6),
                                       '{:,.1f}'.format(num_ided(calc_dict[key1][key2]) / 10.0**6),
                                       '{:.2f}'.format(100 * charity_wmtr(calc_cl)),
                                       currency_fmt(num_charity(calc_dict[key1][key2])),
                                       currency_fmt(ten_year_cost(calc_cl, calc_dict[key1][key2]))])
        data_table.add_hline()


def v2_table(doc, column_list=column_list, table_vars_dict=table_vars_dict):
    global token_list
    token_list = []
    head_str = "X[l]"
    for var in column_list:
        head_str += " X[c]"
        try:
            token_list.append(table_vars_dict[var])
        except ValueError:
            print(var + ' is not a defined table variable. You must add it to the dictionary.')

    # begin generating table
    with doc.create(LongTabu(head_str, row_height=2.0)) as data_table:
        data_table.add_hline()
        data_table.add_row(column_list)
        for key in calc_dict:
            key1 = key
            for key in calc_dict[key]:
                    key2 = key
                    global ex_token_list
                    ex_token_list = []
                    for token in token_list:
                        ex_token = eval(token)
                        ex_token_list.append(ex_token)
                    data_table.add_row(ex_token_list)
        data_table.add_hline()


def make_rows():
    row_wage = ["Wage and Salary Income"]
    row_ltcg = ["Long-term Capital Gains"]
    row_stcg = ["Short-Term Capital Gains"]
    row_tint = ["Interest Income"]
    row_qdiv = ["Qualified Dividends"]
    for key in ref_dict:
        row_wage.append('{:,.1f}'.format(wavgMTR_wages(calc_dict[key][baseline_behavior_name]) * 100.))
        row_ltcg.append('{:,.1f}'.format(wavgMTR_ltcg(calc_dict[key][baseline_behavior_name]) * 100.))
        row_stcg.append('{:,.1f}'.format(wavgMTR_stcg(calc_dict[key][baseline_behavior_name]) * 100.))
        row_tint.append('{:,.1f}'.format(wavgMTR_int(calc_dict[key][baseline_behavior_name]) * 100.))
        row_qdiv.append('{:,.1f}'.format(wavgMTR_qdiv(calc_dict[key][baseline_behavior_name]) * 100.))
    allrows = [row_wage, row_ltcg, row_stcg, row_tint, row_qdiv]
    return allrows


def h_table(doc):
    head_str = "X[l]"
    col_names = ["Income Type"]
    for key in ref_dict:
        head_str += " X[c]"
        col_names.append(key)
    rowlist = make_rows()
    with doc.create(LongTabu(head_str, row_height=2.0)) as data_table:
        data_table.add_hline()
        data_table.add_row(col_names)
        data_table.add_hline()
        data_table.add_row(rowlist[0])
        data_table.add_row(rowlist[1])
        data_table.add_row(rowlist[2])
        data_table.add_row(rowlist[3])
        data_table.add_row(rowlist[4])
        data_table.add_hline()


def notes(doc):
    doc.append(Command('newgeometry', 'top=1in,bottom=1in'))
    with doc.create(Section('Modeling Notes')):
        with doc.create(Subsection('Tax-Calculator')):
            doc.append(tax_calculator_string)
            with doc.create(Subsection('Modeling Assumptions')):
                doc.append(modeling_assumptions_string)


def graphs(fname, width, *args, **kwargs):
     with doc.create(Section(fname)):
        with doc.create(Figure(position='h')) as plot1:
            plot1.add_plot(width=NoEscape(width), *args, **kwargs)
            line_graph(single_data, ylabel="Single Effective Marginal Tax Rate")
        with doc.create(Figure(position='h')) as plot2:
            plot2.add_plot(width=NoEscape(width), *args, **kwargs)
            line_graph(joint_data, ylabel="Joint Effective Marginal Tax Rate")


def author(doc):
    doc.append(NoEscape(r'\noindent\\'))
    doc.append(Command('textbf', paper_author + ' '))
    doc.append(paper_bio)


def logo_footer(doc):
    doc.append(NoEscape(r'\begin{table}[!b]'))
    doc.append(NoEscape(r'\begin{longtabu}{X[c] X[c]}'))
    doc.append(NoEscape(r'\includegraphics[width=80px]{aei_logo2.jpg} & \includegraphics[width=160px]{ospc_logo.png}\\%'))
    doc.append(NoEscape(r' & \\%'))
    doc.append(NoEscape(r'\end{longtabu}%'))
    doc.append(NoEscape(r'\end{table}'))
    doc.append(NoEscape(r'\end{document}'))


# baseline (current law)
policy_cl = Policy()
behavior_cl = Behavior()
records_cl = Records(records_url)
calc_cl = Calculator(policy_cl, records_cl, behavior_cl)
for i in range(start_year - 2013):
    calc_cl.increment_year()
assert calc_cl.current_year == start_year
calc_cl.calc_all()
print("Done")


dict_calculator(ref_dict, start_year, beh_dict, records_url)
dict_ten_year_cost(calc_dict, calc_cl)
dict_ten_year_cost_PE(calc_cl, tyc_beh, calc_dict)
