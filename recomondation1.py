import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Lecture du fichier
data = pd.read_csv("Coursera.csv")

# Supprimer les colonnes inutiles
data = data[['Course Name', 'Difficulty Level', 'Course Description', 'Skills', 'Course Rating']]

# Nettoyage des colonnes
for col in ['Course Name', 'Course Description', 'Skills']:
    data[col] = data[col].astype(str)  # Assurer que tout est string
    data[col] = data[col].str.replace('[,:()_]', '', regex=True)
    data[col] = data[col].str.replace(' +', ' ', regex=True).str.strip()

# Création de la colonne "tags"
data['tags'] = data['Course Name'] + ' ' + data['Difficulty Level'] + ' ' + data['Course Description'] + ' ' + data['Skills']

# Création d’un nouveau DataFrame
new_df = data[['Course Name', 'tags', 'Course Rating']].copy()
new_df.rename(columns={'Course Name': 'course_name'}, inplace=True)
new_df['tags'] = new_df['tags'].str.lower()

# Stemming
import nltk
nltk.download('punkt')
from nltk.stem.porter import PorterStemmer

ps = PorterStemmer()

def stem(text):
    return " ".join([ps.stem(word) for word in text.split()])

new_df['tags'] = new_df['tags'].apply(stem)

# Vectorisation
from sklearn.feature_extraction.text import CountVectorizer
cv = CountVectorizer(max_features=5000, stop_words='english')
vectors = cv.fit_transform(new_df['tags']).toarray()

# Calcul de la similarité
from sklearn.metrics.pairwise import cosine_similarity
similarity = cosine_similarity(vectors)

# Fonction de recommandation
def recommend(course):
    if course not in new_df['course_name'].values:
        print("❌ Course not found. Try another course name.")
        return

    course_index = new_df[new_df['course_name'] == course].index[0]
    distances = similarity[course_index]
    course_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:7]

    print(f"\n📚 Recommended courses for: {course}\n")
    for i in course_list:
        course_name = new_df.iloc[i[0]].course_name
        rating = new_df.iloc[i[0]]['Course Rating']
        print(f"✔ {course_name} — Rating: {rating}")

# Exemple d'appel
recommend("Business Strategy Business Model Canvas Analysis with Miro")
