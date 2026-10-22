"""Папка снимков 3D-видов котельной для листа ТМ-6 (рабочая — ../m3d/tmshots2, в репозитории — out/tmshots)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, '..', 'm3d', 'tmshots2')
if not os.path.isdir(os.path.join(HERE, '..', 'm3d')):
    SHOTS = os.path.join(HERE, 'out', 'tmshots')
os.makedirs(SHOTS, exist_ok=True)
