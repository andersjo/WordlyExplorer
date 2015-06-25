import matplotlib.pyplot as plt
import numpy as np
import cStringIO
import seaborn as sns

from kartograph import Kartograph


# Use seaborn
sns.set()
#sns.set_context("talk")
# sns.palplot(sns.color_palette()) # This causes a bunch of error messages to be displayed...QPixmap: It is not safe to use pixmaps outside the GUI thread


def hist_ages_gender(term, statsM, statsF, xticks, xticknames, ylim, min_age=10, max_age=90, num_bins=9):

    fig = plt.figure() # Fig name just to be able to close it again
    plt.title('Age and gender distribution for:     ' + term + '')
    plt.xlabel('Age range')
    plt.ylabel('Number of people')


    bar_width = 0.35
    displace = bar_width/2
    plt.bar(np.array(xticks) + displace, statsM, bar_width, align='edge', label='Male', color='b')
    plt.bar(np.array(xticks) + displace + bar_width, statsF, bar_width, align='edge', label='Female', color='g')
    plt.xticks(xticks, xticknames)
    plt.ylim(ylim)

    plt.legend()
    plt.tight_layout()
    sio = cStringIO.StringIO()
    plt.savefig(sio, format="jpg")
    plt.close(fig) # Close figures to save mem
    return sio

