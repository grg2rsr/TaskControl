# %%
"""
 
    ###    ##    ## ######## ####  ######  #### ########     ###    ########  #######  ########  ##    ##    ########  ########    ###     ######  ##     ## 
   ## ##   ###   ##    ##     ##  ##    ##  ##  ##     ##   ## ##      ##    ##     ## ##     ##  ##  ##     ##     ## ##         ## ##   ##    ## ##     ## 
  ##   ##  ####  ##    ##     ##  ##        ##  ##     ##  ##   ##     ##    ##     ## ##     ##   ####      ##     ## ##        ##   ##  ##       ##     ## 
 ##     ## ## ## ##    ##     ##  ##        ##  ########  ##     ##    ##    ##     ## ########     ##       ########  ######   ##     ## ##       ######### 
 ######### ##  ####    ##     ##  ##        ##  ##        #########    ##    ##     ## ##   ##      ##       ##   ##   ##       ######### ##       ##     ## 
 ##     ## ##   ###    ##     ##  ##    ##  ##  ##        ##     ##    ##    ##     ## ##    ##     ##       ##    ##  ##       ##     ## ##    ## ##     ## 
 ##     ## ##    ##    ##    ####  ######  #### ##        ##     ##    ##     #######  ##     ##    ##       ##     ## ######## ##     ##  ######  ##     ## 
 
"""

# Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
# Nicknames = ['Therapist']
# Nicknames = ['Teacher']
# task_name = 'learn_to_choose_v2'

# # get animals by Nickname
# folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
# Animals = utils.get_Animals(folder)
# Animals = [a for a in Animals if a.Nickname in Nicknames]

def plot_anticipatory_reaches_over_sessions(Animal_folder, save=None):
    Animal = utils.Animal(Animal_folder)

    SessionsDf = utils.get_sessions(Animal.folder)
    SessionsDf = SessionsDf.groupby('task').get_group(task_name)
    from Utils import metrics as m

    for i, row in SessionsDf.iterrows():
        session_folder = Path(row['path'])
        LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
        metrics = (m.get_start, m.get_stop, m.has_choice, m.get_correct_side, m.get_chosen_side, m.has_anticipatory_reach)
        SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics)

        try:
            n_choices = SessionDf.groupby('has_choice').get_group(True).shape[0]
            n_trials = SessionDf.shape[0]
            Df = groupby_dict(SessionDf, dict(has_choice=True, has_anticip_reach=True))
            try:
                SessionsDf.loc[i,'f_anticip_left'] = groupby_dict(SessionDf, dict(has_choice=True, has_anticip_reach=True, chosen_side='left')).shape[0] / n_trials
            except KeyError:
                SessionsDf.loc[i,'f_anticip_left'] = 0
                pass        
            try:
                SessionsDf.loc[i,'f_anticip_right'] = groupby_dict(SessionDf, dict(has_choice=True, has_anticip_reach=True, chosen_side='right')).shape[0] / n_trials
            except KeyError:
                SessionsDf.loc[i,'f_anticip_right'] = 0
                pass
        except KeyError:
            SessionsDf.loc[i,'f_anticip_left'] = 0
            SessionsDf.loc[i,'f_anticip_right'] = 0
            pass

    fig, axes = plt.subplots()
    tvec = range(SessionsDf.shape[0])

    colors = dict(zip(('left','right'), sns.color_palette(palette='PiYG',n_colors=2)))
    colors['both'] = 'black'

    # axes.plot(tvec, anticip_reaches)
    axes.plot(tvec, SessionsDf['f_anticip_left'].values, color=colors['left'])
    axes.plot(tvec, SessionsDf['f_anticip_right'].values, color=colors['right'])
    axes.plot(tvec, SessionsDf['f_anticip_left'].values + SessionsDf['f_anticip_right'].values, color=colors['both'])
    axes.set_title('anticipatory reaches over days')
    axes.set_xticks(range(SessionsDf.shape[0]))
    axes.set_xticklabels(SessionsDf['date'],rotation=45, ha="right")
    axes.set_xlabel('date')
    axes.set_ylabel('fraction of trials\nwith anticip. reach')
    # axes.set_ylim(0,0.5)
    sns.despine(fig)

    title = Animal.Nickname + ' - anticipatory reaches'
    axes.set_title(title)
    fig.tight_layout()

    if save is not None:
        os.makedirs(session_folder / 'plots', exist_ok=True)
        plt.savefig(save, dpi=600)
        plt.close(fig)


# %%
"""
 
 ########  ########  ######## ##     ##    ###    ######## ##     ## ########  ########    ########  ########    ###     ######  ##     ## ########  ######  
 ##     ## ##     ## ##       ###   ###   ## ##      ##    ##     ## ##     ## ##          ##     ## ##         ## ##   ##    ## ##     ## ##       ##    ## 
 ##     ## ##     ## ##       #### ####  ##   ##     ##    ##     ## ##     ## ##          ##     ## ##        ##   ##  ##       ##     ## ##       ##       
 ########  ########  ######   ## ### ## ##     ##    ##    ##     ## ########  ######      ########  ######   ##     ## ##       ######### ######    ######  
 ##        ##   ##   ##       ##     ## #########    ##    ##     ## ##   ##   ##          ##   ##   ##       ######### ##       ##     ## ##             ## 
 ##        ##    ##  ##       ##     ## ##     ##    ##    ##     ## ##    ##  ##          ##    ##  ##       ##     ## ##    ## ##     ## ##       ##    ## 
 ##        ##     ## ######## ##     ## ##     ##    ##     #######  ##     ## ########    ##     ## ######## ##     ##  ######  ##     ## ########  ######  
 
"""

Nicknames = ['Lifeguard', 'Lumberjack', 'Teacher', 'Plumber', 'Poolboy', 'Policeman', 'Therapist']
Nicknames = ['Therapist']
Nicknames = ['Teacher']
task_name = 'learn_to_choose_v2'

# get animals by Nickname
folder = Path("/media/georg/htcondor/shared-paton/georg/Animals_reaching")
Animals = utils.get_Animals(folder)
Animals = [a for a in Animals if a.Nickname in Nicknames]

# %%
Animal = Animals[0]
SessionsDf = utils.get_sessions(Animal.folder)
SessionsDf = SessionsDf.groupby('task').get_group(task_name)
from Utils import metrics as m


for i, row in SessionsDf.iterrows():
    session_folder = Path(row['path'])
    LogDf = bhv.get_LogDf_from_path(session_folder / "arduino_log.txt")
    metrics = (m.get_start, m.get_stop, m.has_choice, m.get_correct_side, m.get_chosen_side, m.has_premature_reach, m.has_premature_choice)
    SessionDf, TrialDfs = bhv.get_SessionDf(LogDf, metrics)

    try:
        n_choices = SessionDf.groupby('has_choice').get_group(True).shape[0]
        n_trials = SessionDf.shape[0]
        Df = groupby_dict(SessionDf, dict(has_choice=True, has_premature_reach=True))
        try:
            SessionsDf.loc[i,'f_prem_reach_left'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_reach=True, chosen_side='left')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_reach_left'] = 0
            pass        
        try:
            SessionsDf.loc[i,'f_prem_reach_right'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_reach=True, chosen_side='right')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_reach_right'] = 0
            pass
    except KeyError:
        SessionsDf.loc[i,'f_prem_reach_left'] = 0
        SessionsDf.loc[i,'f_prem_reach_right'] = 0
        pass

    try:
        n_choices = SessionDf.groupby('has_choice').get_group(True).shape[0]
        n_trials = SessionDf.shape[0]
        Df = groupby_dict(SessionDf, dict(has_choice=True, has_premature_choice=True))
        try:
            SessionsDf.loc[i,'f_prem_choice_left'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_choice=True, chosen_side='left')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_choice_left'] = 0
            pass        
        try:
            SessionsDf.loc[i,'f_prem_choice_right'] = groupby_dict(SessionDf, dict(has_choice=True, has_premature_choice=True, chosen_side='right')).shape[0] / n_trials
        except KeyError:
            SessionsDf.loc[i,'f_prem_choice_right'] = 0
            pass
    except KeyError:
        SessionsDf.loc[i,'f_prem_choice_left'] = 0
        SessionsDf.loc[i,'f_prem_choice_right'] = 0
        pass


#%%
fig, axes = plt.subplots(nrows=2,sharex=True,sharey=True)
tvec = range(SessionsDf.shape[0])


import matplotlib as mpl
colors = dict(left=mpl.cm.PiYG(0.05),
              right=mpl.cm.PiYG(0.95),
              both='black')

# axes.plot(tvec, anticip_reaches)
axes[0].plot(tvec, SessionsDf['f_prem_reach_left'].values, color=colors['left'])
axes[0].plot(tvec, SessionsDf['f_prem_reach_right'].values, color=colors['right'])
axes[0].plot(tvec, SessionsDf['f_prem_reach_left'].values + SessionsDf['f_prem_reach_right'].values, color=colors['both'])

axes[1].plot(tvec, SessionsDf['f_prem_choice_left'].values, color=colors['left'])
axes[1].plot(tvec, SessionsDf['f_prem_choice_right'].values, color=colors['right'])
axes[1].plot(tvec, SessionsDf['f_prem_choice_left'].values + SessionsDf['f_prem_choice_right'].values, color=colors['both'])


axes[0].set_title('premature reaches over days')
axes[1].set_xticks(range(SessionsDf.shape[0]))
axes[1].set_xticklabels(SessionsDf['date'],rotation=45, ha="right")
axes[1].set_xlabel('date')
axes[0].set_ylabel('fraction of trials\nwith premature reach')
axes[1].set_ylabel('fraction of trials\nwith premature choice')
# axes.set_ylim(0,0.5)
sns.despine(fig)
fig.tight_layout()
