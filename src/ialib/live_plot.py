import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

from scipy.stats import norm
from scipy import stats
import numpy as np

from quantiphy import Quantity

style.use("seaborn")

fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)


def animate(i):
    try:
        file = open("dat.txt", "r")
        graph_data = file.read()
        lines = graph_data.split("\n")
        file.close()
        xs = []
        ys = []
        for line in lines:
            if len(line) > 1 and not line.startswith("#"):
                x, y = [float(f) for f in line.split(",")]
                xs.append(x)
                ys.append(y)
        ax1.clear()

        mu, std = norm.fit(ys)

        # Plot the histogram.
        #ax1.hist(ys, density=True, alpha=0.6, color='g')
        plt.scatter(xs, ys)
        # Plot the PDF.
        xmin, xmax = plt.xlim()
        x = np.linspace(xmin, xmax, 100)
        p = norm.pdf(x, mu, std)
        #ax1.plot(x, p, 'k', linewidth=2)
        k2, p = stats.normaltest(ys)
        title = f"Fit results: mu = {Quantity(mu, 'Ohm')},  std = {Quantity(std, 'Ohm')}, p = {p:.3f} (normal if p > 0.05)"
        plt.title(title)
    except Exception as e:
        print(e)

animate(None)
ani = animation.FuncAnimation(fig, animate, interval=100)
plt.show()
