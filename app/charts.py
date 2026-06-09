from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from matplotlib.ticker import MaxNLocator

from ui_theme import chart_palette, style_matplotlib_figure


def _show_figure(fig):
    st.pyplot(fig)
    plt.close(fig)


def plot_student_result(answers, total):
    if total <= 0:
        st.info("Sem perguntas para exibir o gráfico.")
        return
    pal = chart_palette()
    correct = sum(answers)
    wrong = total - correct
    fig, ax = plt.subplots()
    ax.pie(
        [correct, wrong],
        labels=["Acertos", "Erros"],
        autopct="%1.1f%%",
        colors=[pal["correct"], pal["wrong"]],
        startangle=90,
        textprops={"color": pal["text"]},
    )
    ax.axis("equal")
    style_matplotlib_figure(fig, ax, grid=False)
    _show_figure(fig)


def plot_leaderboard_comparison(leaderboard):
    if not leaderboard:
        st.info("Nenhum aluno cadastrado ainda.")
        return
    pal = chart_palette()
    df = pd.DataFrame(leaderboard)
    df["porcentagem"] = (df["score"] / df["total"]) * 100
    df = df.sort_values("porcentagem", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(df["name"], df["porcentagem"], color=pal["bar"])
    ax.set_xlabel("Acertos (%)")
    ax.set_title("Comparação de Desempenho entre Alunos")
    ax.invert_yaxis()
    style_matplotlib_figure(fig, ax)
    for i, v in enumerate(df["porcentagem"]):
        ax.text(v + 1, i, f"{v:.1f}%", va="center", color=pal["text"])
    _show_figure(fig)


def plot_score_distribution(best_scores: list[int], total_questions: int):
    """Quantos alunos ficaram em cada nota (melhor tentativa de cada um)."""
    if not best_scores or total_questions <= 0:
        return
    pal = chart_palette()
    counts = [best_scores.count(s) for s in range(total_questions + 1)]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(total_questions + 1), counts, color=pal["bar"])
    ax.set_xticks(range(total_questions + 1))
    ax.set_xlabel("Acertos (melhor tentativa)")
    ax.set_ylabel("Nº de alunos")
    ax.set_title("Distribuição de notas")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    style_matplotlib_figure(fig, ax)
    for i, c in enumerate(counts):
        if c:
            ax.text(i, c + 0.05, str(c), ha="center", color=pal["text"])
    _show_figure(fig)


def plot_completion_donut(completed: int, pending: int, target: int):
    """Proporção de alunos que concluíram (atingiram a meta) vs abaixo dela."""
    if completed + pending <= 0:
        return
    pal = chart_palette()
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.pie(
        [completed, pending],
        labels=[f"{target}+ acertos", f"Abaixo de {target}"],
        autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
        colors=[pal["correct"], pal["wrong"]],
        startangle=90,
        wedgeprops={"width": 0.45},
        textprops={"color": pal["text"]},
    )
    ax.axis("equal")
    ax.set_title("Aproveitamento da turma")
    style_matplotlib_figure(fig, ax, grid=False)
    _show_figure(fig)


def plot_attempts_comparison(leaderboard):
    """Evolução dos alunos que usaram a segunda tentativa (1ª vs 2ª)."""
    first: dict[str, int] = {}
    second: dict[str, int] = {}
    for e in leaderboard:
        n = e["name"]
        if n not in first:
            first[n] = e["score"]
        elif n not in second:
            second[n] = e["score"]
    names = list(second)
    if not names:
        st.info("Nenhum aluno fez a segunda tentativa ainda.")
        return
    pal = chart_palette()
    x = range(len(names))
    w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([i - w / 2 for i in x], [first[n] for n in names], width=w, label="1ª tentativa", color=pal["performance"])
    ax.bar([i + w / 2 for i in x], [second[n] for n in names], width=w, label="2ª tentativa", color=pal["bar"])
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("Acertos")
    ax.set_title("Evolução: 1ª vs 2ª tentativa")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    style_matplotlib_figure(fig, ax)
    legend = ax.legend()
    legend.get_frame().set_facecolor(pal["figure"])
    legend.get_frame().set_edgecolor(pal["grid"])
    for text in legend.get_texts():
        text.set_color(pal["text"])
    _show_figure(fig)


def plot_question_performance(leaderboard, total_questions):
    if not leaderboard or total_questions <= 0:
        return
    pal = chart_palette()
    pergunta_acertos = [0] * total_questions
    for aluno in leaderboard:
        for i, acertou in enumerate(aluno["responses"]):
            if i < total_questions and acertou:
                pergunta_acertos[i] += 1
    num_alunos = len(leaderboard)
    percentuais = [(acertos / num_alunos) * 100 for acertos in pergunta_acertos]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(range(1, total_questions + 1), percentuais, color=pal["performance"])
    ax.set_xticks(range(1, total_questions + 1))
    ax.set_xlabel("Número da Pergunta")
    ax.set_ylabel("Alunos que acertaram (%)")
    ax.set_title("Taxa de Acertos por Pergunta (todos os alunos)")
    ax.set_ylim(0, 100)
    style_matplotlib_figure(fig, ax)
    for i, p in enumerate(percentuais):
        ax.text(i + 1, p + 1, f"{p:.1f}%", ha="center", color=pal["text"])
    _show_figure(fig)
