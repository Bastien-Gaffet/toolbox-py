#!/usr/bin/env python3
"""
toolbox_gui.py
Interface graphique (PySide6) de la boîte à outils.

Réutilise le socle `toolbox_core` (découverte des outils via le README,
dépendances, exécution). Chaque outil est lancé dans un QProcess séparé ;
sa sortie s'affiche en direct, et on peut lui envoyer des réponses au clavier
(pour les invites type [o/N]).

Usage :
    python toolbox_gui.py

Dépendances :
    pip install PySide6
"""

import sys

import toolbox_core as core

try:
    from PySide6.QtCore import Qt, QProcess, QProcessEnvironment
    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QSplitter, QTreeWidget,
        QTreeWidgetItem, QLineEdit, QPushButton, QPlainTextEdit, QLabel,
        QVBoxLayout, QHBoxLayout, QFrame, QMessageBox, QStatusBar,
    )
except ImportError:
    print("PySide6 est requis : pip install PySide6")
    sys.exit(1)


STYLE = """
QMainWindow, QWidget { background: #1e1f26; color: #e6e6e6; }
QLabel#titre { font-size: 15pt; font-weight: bold; color: #7fd7ff; }
QLabel#desc { color: #b7b7c0; }
QTreeWidget {
    background: #24252e; border: 1px solid #33343f; border-radius: 6px;
    outline: 0;
}
QTreeWidget::item { padding: 4px; }
QTreeWidget::item:selected { background: #2f6b8f; color: #ffffff; }
QLineEdit {
    background: #24252e; border: 1px solid #3a3b47; border-radius: 6px;
    padding: 6px; color: #e6e6e6;
}
QLineEdit:focus { border: 1px solid #5fb0d8; }
QPlainTextEdit {
    background: #17181e; border: 1px solid #33343f; border-radius: 6px;
    color: #d6f5d6; font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 10pt;
}
QPushButton {
    background: #2f6b8f; border: none; border-radius: 6px;
    padding: 7px 14px; color: #ffffff; font-weight: bold;
}
QPushButton:hover { background: #3a83ad; }
QPushButton:disabled { background: #3a3b47; color: #7a7a85; }
QPushButton#secondaire { background: #3a3b47; }
QPushButton#secondaire:hover { background: #4a4b59; }
QPushButton#danger { background: #8f3a3a; }
QPushButton#danger:hover { background: #a84545; }
QFrame#bandeau { background: #4a3f1e; border: 1px solid #6b5a2a; border-radius: 6px; }
"""


class FenetrePrincipale(QMainWindow):
    def __init__(self):
        super().__init__()
        self.proc: QProcess | None = None
        self.script_courant: str | None = None
        self.outils = core.charger_outils()

        self.setWindowTitle("🧰 toolbox-py")
        self.resize(1040, 660)
        self._construire_ui()
        self._peupler_arbre()
        self._verifier_dependances()

    # ── Construction de l'interface ─────────────────────────────────────────
    def _construire_ui(self):
        total = sum(len(v) for v in self.outils.values())

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Bandeau dépendances manquantes (masqué par défaut)
        self.bandeau = QFrame(objectName="bandeau")
        self.bandeau.hide()
        bl = QHBoxLayout(self.bandeau)
        self.bandeau_label = QLabel()
        self.bandeau_btn = QPushButton("Installer")
        self.bandeau_btn.clicked.connect(self._installer_dependances)
        bl.addWidget(self.bandeau_label, 1)
        bl.addWidget(self.bandeau_btn)
        layout.addWidget(self.bandeau)

        # Splitter : arbre à gauche, panneau à droite
        split = QSplitter(Qt.Horizontal)

        # ── Gauche : recherche + arbre ──
        gauche = QWidget()
        gl = QVBoxLayout(gauche)
        gl.setContentsMargins(0, 0, 0, 0)
        titre_g = QLabel(f"🧰 toolbox-py  ·  {total} outils")
        titre_g.setObjectName("titre")
        gl.addWidget(titre_g)
        self.recherche = QLineEdit(placeholderText="🔎 Filtrer les outils…")
        self.recherche.textChanged.connect(self._peupler_arbre)
        gl.addWidget(self.recherche)
        self.arbre = QTreeWidget()
        self.arbre.setHeaderHidden(True)
        self.arbre.currentItemChanged.connect(self._selection_changee)
        self.arbre.itemDoubleClicked.connect(lambda *_: self._lancer())
        gl.addWidget(self.arbre, 1)
        split.addWidget(gauche)

        # ── Droite : détails + arguments + sortie ──
        droite = QWidget()
        dl = QVBoxLayout(droite)
        dl.setContentsMargins(0, 0, 0, 0)

        self.titre = QLabel("Sélectionnez un outil")
        self.titre.setObjectName("titre")
        self.desc = QLabel("")
        self.desc.setObjectName("desc")
        self.desc.setWordWrap(True)
        dl.addWidget(self.titre)
        dl.addWidget(self.desc)

        # Ligne arguments + boutons
        ligne = QHBoxLayout()
        self.args = QLineEdit(placeholderText='Arguments — ex : "D:\\Photos" --simulation')
        self.args.returnPressed.connect(self._lancer)
        self.btn_lancer = QPushButton("▶  Lancer")
        self.btn_lancer.clicked.connect(self._lancer)
        self.btn_aide = QPushButton("❔  Aide", objectName="secondaire")
        self.btn_aide.clicked.connect(lambda: self._lancer(aide=True))
        self.btn_stop = QPushButton("⏹  Arrêter", objectName="danger")
        self.btn_stop.clicked.connect(self._arreter)
        self.btn_stop.setEnabled(False)
        ligne.addWidget(self.args, 1)
        ligne.addWidget(self.btn_lancer)
        ligne.addWidget(self.btn_aide)
        ligne.addWidget(self.btn_stop)
        dl.addLayout(ligne)

        # Sortie
        self.sortie = QPlainTextEdit(readOnly=True)
        self.sortie.setPlaceholderText("La sortie du programme s'affichera ici.")
        dl.addWidget(self.sortie, 1)

        # Ligne d'envoi vers le programme (invites [o/N], etc.)
        ligne2 = QHBoxLayout()
        self.entree = QLineEdit(placeholderText="↳ Répondre au programme (Entrée pour envoyer)…")
        self.entree.setEnabled(False)
        self.entree.returnPressed.connect(self._envoyer_entree)
        self.btn_envoyer = QPushButton("Envoyer", objectName="secondaire")
        self.btn_envoyer.setEnabled(False)
        self.btn_envoyer.clicked.connect(self._envoyer_entree)
        ligne2.addWidget(self.entree, 1)
        ligne2.addWidget(self.btn_envoyer)
        dl.addLayout(ligne2)

        split.addWidget(droite)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([320, 720])
        layout.addWidget(split, 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Prêt")
        self._maj_boutons(actif=False)

    # ── Arbre des outils ────────────────────────────────────────────────────
    def _peupler_arbre(self, filtre: str = ""):
        filtre = (filtre or "").lower().strip()
        self.arbre.clear()
        for categorie, liste in self.outils.items():
            visibles = [
                (s, d) for s, d in liste
                if not filtre or filtre in s.lower() or filtre in d.lower()
            ]
            if not visibles:
                continue
            parent = QTreeWidgetItem([f"{categorie}  ({len(visibles)})"])
            parent.setFlags(parent.flags() & ~Qt.ItemIsSelectable)
            f = parent.font(0)
            f.setBold(True)
            parent.setFont(0, f)
            self.arbre.addTopLevelItem(parent)
            for script, desc in visibles:
                enfant = QTreeWidgetItem([script])
                enfant.setData(0, Qt.UserRole, (script, desc))
                enfant.setToolTip(0, desc)
                parent.addChild(enfant)
            parent.setExpanded(True)

    def _selection_changee(self, courant, _prec):
        donnees = courant.data(0, Qt.UserRole) if courant else None
        if not donnees:
            return
        script, desc = donnees
        self.script_courant = script
        self.titre.setText(script)
        self.desc.setText(desc)

    # ── Exécution ───────────────────────────────────────────────────────────
    def _lancer(self, aide: bool = False):
        if self.proc is not None:
            QMessageBox.information(self, "Occupé",
                                    "Un outil est déjà en cours. Arrêtez-le d'abord.")
            return
        if not self.script_courant:
            self.statusBar().showMessage("Sélectionnez d'abord un outil.")
            return

        args = ["--help"] if aide else core.decouper_args(self.args.text())
        commande = core.commande_pour(self.script_courant, args)

        self.sortie.clear()
        self.sortie.appendPlainText(f"$ python {self.script_courant} {' '.join(args)}\n")

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONIOENCODING", "utf-8")

        self.proc = QProcess(self)
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._lire_sortie)
        self.proc.finished.connect(self._processus_fini)
        self.proc.errorOccurred.connect(self._processus_erreur)
        self.proc.start(commande[0], commande[1:])

        self.statusBar().showMessage(f"En cours : {self.script_courant}")
        self._maj_boutons(actif=True)

    def _lire_sortie(self):
        if not self.proc:
            return
        donnees = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        # Nettoyer les retours chariot (barres de progression) pour l'affichage
        for morceau in donnees.replace("\r\n", "\n").split("\r"):
            morceau = morceau.rstrip("\n")
            if morceau:
                self.sortie.appendPlainText(morceau)

    def _processus_fini(self, code, _statut):
        self.sortie.appendPlainText(
            f"\n{'✓' if code == 0 else '✗'} Terminé (code {code}).")
        self.statusBar().showMessage(
            f"Terminé (code {code}).", 5000)
        self.proc = None
        self._maj_boutons(actif=False)

    def _processus_erreur(self, _err):
        if self.proc:
            self.sortie.appendPlainText(
                "\n✗ Impossible de lancer le processus (Python introuvable ?).")

    def _arreter(self):
        if self.proc:
            self.proc.kill()
            self.statusBar().showMessage("Outil arrêté.", 3000)

    def _envoyer_entree(self):
        if not self.proc:
            return
        texte = self.entree.text()
        self.proc.write((texte + "\n").encode("utf-8"))
        self.sortie.appendPlainText(f"> {texte}")
        self.entree.clear()

    def _maj_boutons(self, actif: bool):
        self.btn_lancer.setEnabled(not actif)
        self.btn_aide.setEnabled(not actif)
        self.btn_stop.setEnabled(actif)
        self.entree.setEnabled(actif)
        self.btn_envoyer.setEnabled(actif)

    # ── Dépendances ─────────────────────────────────────────────────────────
    def _verifier_dependances(self):
        manquants = core.paquets_manquants()
        if not manquants:
            self.bandeau.hide()
            return
        self._manquants = manquants
        self.bandeau_label.setText(
            "⚠️  Dépendances manquantes : " + ", ".join(manquants)
            + "  — certains outils ne fonctionneront pas.")
        self.bandeau.show()

    def _installer_dependances(self):
        if self.proc is not None:
            return
        self.bandeau_btn.setEnabled(False)
        self.sortie.clear()
        commande = core.commande_pip_install(self._manquants)
        self.sortie.appendPlainText(f"$ {' '.join(commande)}\n")

        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._lire_sortie)
        self.proc.finished.connect(self._install_fini)
        self.proc.start(commande[0], commande[1:])
        self.statusBar().showMessage("Installation des dépendances…")
        self._maj_boutons(actif=True)

    def _install_fini(self, code, _statut):
        self.proc = None
        self._maj_boutons(actif=False)
        self.bandeau_btn.setEnabled(True)
        if code == 0:
            self.sortie.appendPlainText("\n✓ Dépendances installées.")
            self._verifier_dependances()
        else:
            self.sortie.appendPlainText(f"\n✗ Échec de l'installation (code {code}).")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    fenetre = FenetrePrincipale()
    fenetre.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
