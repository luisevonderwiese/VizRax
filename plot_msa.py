import matplotlib.patches as patches
import matplotlib.pyplot as plt
from Bio import AlignIO


def get_color(symbol):
    if symbol == "A":
        return "dodgerblue"
    if symbol == "C":
        return "firebrick"
    if symbol == "G":
        return "green"
    if symbol == "T":
        return "gold"
    return "grey"



align = AlignIO.read("msa/animal.phy", "phylip-relaxed")
m = align.get_alignment_length()
n = len(align)

fig_h = 10
fig_w = 40
spacing_h = 0.02
spacing_w = 0.001
block_w = (1 - (m - 1) * spacing_w) / m
block_h = (1 - (n - 1) * spacing_h) / n
fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
plt.axis('off')
for i in range(n):
    y_pos = 1 - (i+1) * block_h - i * spacing_h
    for j in range(m):
        x_pos = j * (block_w + spacing_w)
        color = get_color(align[i, j])
        rect = patches.Rectangle((x_pos, y_pos), block_w, block_h, color = color)
        ax.add_patch(rect)
plt.savefig("msa_plots/animal.png", bbox_inches='tight')
