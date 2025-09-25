import requests
import time
import statistics
from collections import deque
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import os
from dotenv import load_dotenv

# --- CHARGEMENT VARIABLES ENV ---
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# --- CONFIGURATION API CRASH ---
URL = "https://crash-gateway-grm-cr.100hp.app/history"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "customer-id": "077dee8d-c923-4c02-9bee-757573662e69",
    "session-id": "bbaabe97-6d00-43f8-8570-d88e3e385009",
    "origin": "https://1play.gamedev-tech.cc",
    "referer": "https://1play.gamedev-tech.cc/",
    "user-agent": "Mozilla/5.0"
}
SLEEP = 0.2
HISTO_MAX = 10000

# --- CLAVIERS TELEGRAM ---
main_keyboard_user = [["PREDICTION Lucky Jet","Mon compte","Statistiques"]]
main_keyboard_admin = [["PREDICTION Lucky Jet","Mon compte","Statistiques","Admin"]]
prediction_keyboard = [["Signal","Signal Montant","Signal Premium"],["Retour"]]
admin_keyboard = [["Ajouter","Réduire","Désactiver"],["Retour"]]

admin_actions = {}

# --- ANALYSE INTELLIGENTE ---
class AnalyseCrash:
    def __init__(self):
        self.coeffs = deque(maxlen=HISTO_MAX)
        self.hashs_enregistres = set()

    def ajouter_tour(self, tour_hash, coeff):
        if tour_hash in self.hashs_enregistres or coeff is None:
            return False
        self.hashs_enregistres.add(tour_hash)
        self.coeffs.append(coeff)
        return True

    def stats_base(self):
        if not self.coeffs: return 0,0,0
        return sum(self.coeffs)/len(self.coeffs), max(self.coeffs), min(self.coeffs)

    def stats_avancees(self):
        if len(self.coeffs)<2: return 0,0
        return statistics.variance(self.coeffs), statistics.stdev(self.coeffs)

    def moyenne_mobile(self,N=10):
        data=list(self.coeffs)
        if len(data)<N: N=len(data)
        return sum(data[-N:])/N

    def seuils_adaptatifs(self):
        if len(self.coeffs)<2: return 2,5
        moyenne = sum(self.coeffs)/len(self.coeffs)
        ecart = statistics.stdev(self.coeffs)
        bas = max(0.5, moyenne - ecart)
        haut = max(moyenne + ecart, bas+0.5)
        return bas, haut

    def patterns(self):
        pattern_BH=0
        pattern_HB=0
        data=list(self.coeffs)
        for i in range(1,len(data)):
            if data[i-1]<2 and data[i]>=2: pattern_BH+=1
            if data[i-1]>=2 and data[i]<2: pattern_HB+=1
        return pattern_BH, pattern_HB

    def detecter_sequences_anomalies(self):
        sequences=[]
        anomalies=[]
        if len(self.coeffs)<2: return sequences, anomalies
        data=list(self.coeffs)
        moyenne=sum(data)/len(data)
        ecart=statistics.stdev(data) if len(data)>1 else 0
        bas_seuil, haut_seuil=self.seuils_adaptatifs()
        seq_type=None
        seq_len=0
        for c in data:
            if c<bas_seuil:
                if seq_type=="bas": seq_len+=1
                else:
                    if seq_len>=3: sequences.append((seq_type,seq_len))
                    seq_type="bas"; seq_len=1
            elif c>haut_seuil:
                if seq_type=="haut": seq_len+=1
                else:
                    if seq_len>=3: sequences.append((seq_type,seq_len))
                    seq_type="haut"; seq_len=1
            else:
                if seq_len>=3: sequences.append((seq_type,seq_len))
                seq_type=None; seq_len=0
            if ecart>0 and abs(c-moyenne)>2*ecart: anomalies.append(c)
        if seq_len>=3: sequences.append((seq_type,seq_len))
        return sequences, anomalies

    def tableau_synthese(self):
        moyenne,max_,min_=self.stats_base()
        variance,ecart=self.stats_avancees()
        bas_seuil,haut_seuil=self.seuils_adaptatifs()
        pattern_BH,pattern_HB=self.patterns()
        sequences,anomalies=self.detecter_sequences_anomalies()
        return {
            "Moyenne":round(moyenne,2),
            "Max":max_,
            "Min":min_,
            "Variance":round(variance,2),
            "EcartType":round(ecart,2),
            "SeuilBas":round(bas_seuil,2),
            "SeuilHaut":round(haut_seuil,2),
            "Pattern_BH":pattern_BH,
            "Pattern_HB":pattern_HB,
            "SequencesLongues":sequences,
            "Anomalies":anomalies,
            "TotalTours":len(self.coeffs)
        }

analyse = AnalyseCrash()

# --- HANDLER TELEGRAM ---
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id==ADMIN_ID:
        update.message.reply_text("Bienvenue Admin",reply_markup=ReplyKeyboardMarkup(main_keyboard_admin, resize_keyboard=True))
    else:
        update.message.reply_text("Bienvenue",reply_markup=ReplyKeyboardMarkup(main_keyboard_user, resize_keyboard=True))

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    user_id = update.effective_user.id

    if text=="Retour":
        if user_id==ADMIN_ID:
            update.message.reply_text("Clavier principal",reply_markup=ReplyKeyboardMarkup(main_keyboard_admin, resize_keyboard=True))
        else:
            update.message.reply_text("Clavier principal",reply_markup=ReplyKeyboardMarkup(main_keyboard_user, resize_keyboard=True))
        return

    if text=="PREDICTION Lucky Jet":
        update.message.reply_text("Choisissez une option",reply_markup=ReplyKeyboardMarkup(prediction_keyboard, resize_keyboard=True))
        return

    if text in ["Signal","Signal Montant","Signal Premium"]:
        update.message.reply_text("Développement en cours")
        return

    if text=="Mon compte":
        username = update.effective_user.username or "Non défini"
        first_name = update.effective_user.first_name or "Non défini"
        signaux_premium = "Non"
        nb_signaux = 5
        msg=(f"Nom: {first_name}\nNom utilisateur: @{username}\nNombre de signaux: {nb_signaux}\nSignal Premium: {signaux_premium}\nID: {user_id}")
        update.message.reply_text(msg)
        return

    if text=="Statistiques":
        tableau = analyse.tableau_synthese()
        msg="📊 Tableau synthèse:\n" + "\n".join(f"{k}: {v}" for k,v in tableau.items())
        update.message.reply_text(msg)
        return

    if user_id==ADMIN_ID:
        if text=="Admin":
            update.message.reply_text("Actions Admin",reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
            return
        if text in ["Ajouter","Réduire","Désactiver"]:
            update.message.reply_text("Veuillez envoyer l'ID de l'utilisateur")
            admin_actions[user_id]=text.lower()+"_id"
            return
        if user_id in admin_actions:
            action = admin_actions[user_id]
            if action.endswith("_id"):
                context.user_data['target_id']=text
                update.message.reply_text("Combien de signaux ?")
                admin_actions[user_id]=action.replace("_id","_nb")
                return
            if action.endswith("_nb"):
                target_id=context.user_data.get('target_id')
                nb=text
                update.message.reply_text(f"Action '{action}' effectuée sur l'utilisateur {target_id} avec {nb} signaux")
                admin_actions.pop(user_id)
                return

# --- INIT BOT ---
updater=Updater(TOKEN,use_context=True)
dp=updater.dispatcher
dp.add_handler(CommandHandler("start",start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
updater.start_polling()

# --- BOUCLE ANALYSE ---
while True:
    try:
        response = requests.get(URL, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        for tour in data:
            tour_hash = tour.get("hash")
            coeff = tour.get("topCoefficient")
            if analyse.ajouter_tour(tour_hash, coeff):
                print(f"🔹 Hash: {tour_hash} | Coefficient: {coeff}")
    except Exception as e:
        print("Erreur:", e)
    time.sleep(SLEEP)