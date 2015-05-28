import matplotlib.pyplot as plt
import numpy as np
import cStringIO
import seaborn as sns


# Use seaborn
sns.set()
#sns.set_context("talk")
# sns.palplot(sns.color_palette()) # This causes a bunch of error messages to be displayed...QPixmap: It is not safe to use pixmaps outside the GUI thread


def hist_ages_gender(term, ages_men, ages_women, total_men, total_women, min_age=10, max_age=90, num_bins=9):

    fig = plt.figure() # Fig name just to be able to close it again
    plt.title('Age and gender distribution for:     ' + term + '')
    plt.xlabel('Age range')
    plt.ylabel('Number of people')

    male_sorted = np.array([value for (key, value) in sorted(ages_men.items())])
    female_sorted = np.array([value for (key, value) in sorted(ages_women.items())])
    total_male_sorted = np.array([float(value) for (key, value) in sorted(total_men.items())])
    total_female_sorted = np.array([float(value) for (key, value) in sorted(total_women.items())])

#    print male_sorted
#    print total_male_sorted
#    print male_sorted/total_male_sorted

    bar_width = 0.35
    displace = bar_width/2
    plt.bar(np.array(range(len(ages_men))) + displace, male_sorted/total_male_sorted, bar_width, align='edge', label='Male', color='b')
    plt.bar(np.array(range(len(ages_women))) + displace + bar_width, female_sorted/total_female_sorted, bar_width, align='edge', label='Female', color='g')
    plt.xticks(range(len(ages_men)), sorted(ages_men))

    plt.legend()
    plt.tight_layout()
    sio = cStringIO.StringIO()
    plt.savefig(sio, format="jpg")
    plt.close(fig) # Close figures to save mem
    return sio
