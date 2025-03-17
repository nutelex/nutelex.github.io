import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from PIL import Image
import subprocess

########################################
# CONFIG
########################################

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")  # Ton token Discord

# Fichier local où sont stockés les pseudos (remplace pseudos.txt)
WORLD_PERM_FILE = "perm/WorldPermissions.PSC"
# L'image sera enregistrée dans pub/sfinx.png
IMAGE_PATH = "pub/sfinx.png"

# Catégories de rôles
CATEGORIES = [
    "SECURITER",
    "BAR",
    "DJ",
    "DIEUX",          # on ne peut pas ajouter ni supprimer
    "ADMIN",
    "BANNEDPLAYERS"
]

########################################
# FONCTIONS GIT AUTO-COMMIT/PUSH
########################################

def commit_and_push(files, message="Update from bot"):
    """
    Ajoute (git add), commit et push la liste de fichiers.
    Nécessite que Git soit configuré (remote, credentials).
    files: liste ou tuple de chemins de fichier.
    """
    try:
        # Ajout des fichiers
        subprocess.run(["git", "add", *files], check=True)

        # Commit
        subprocess.run(["git", "commit", "-m", message], check=True)

        # Push
        subprocess.run(["git", "push"], check=True)

        print("✅ Commit & push OK.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur GIT : {e}")

########################################
# GESTION DES PSEUDOS DANS perm/WorldPermissions.PSC
########################################

def charger_pseudos():
    """
    Lit le fichier perm/WorldPermissions.PSC pour y extraire les pseudos
    répartis dans SECURITER, BAR, DJ, DIEUX, ADMIN, BANNEDPLAYERS.

    Format attendu :
    //AUTO GENERATED DO NOT EDIT!
    //VRCWMT - ...
    //WorldName: ...
    ...

    >> SECURITER > secu
    pseudo1

    >> BAR > bar
    pseudo2

    >> DIEUX > dj+bar+secu+spe
    pseudoX
    ...
    """
    pseudos = {c: set() for c in CATEGORIES}
    if os.path.exists(WORLD_PERM_FILE):
        with open(WORLD_PERM_FILE, "r", encoding="utf-8") as f:
            current_category = None
            for line in f:
                line = line.strip()
                # Repérer ">> XXX > yyy"
                if line.startswith(">> "):
                    # ex: ">> DIEUX > dj+bar+secu+spe"
                    chunk = line.removeprefix(">> ").strip()
                    cat = chunk.split(" > ")[0].strip()  # ex "DIEUX"
                    if cat in pseudos:
                        current_category = cat
                    else:
                        current_category = None
                elif current_category and line:
                    pseudos[current_category].add(line)
    return pseudos

def sauvegarder_pseudos(pseudos):
    """
    Sauvegarde les pseudos dans perm/WorldPermissions.PSC,
    puis commit/push automatiquement.
    """
    os.makedirs("perm", exist_ok=True)  # s'assure que le dossier perm existe
    with open(WORLD_PERM_FILE, "w", encoding="utf-8") as f:
        f.write("//AUTO GENERATED DO NOT EDIT!\n")
        f.write("//VRCWMT - UTC 10/3/25 12:06 AM - V1.4.0\n")
        f.write("//WorldName: MURDER DRONES\n")
        f.write("//WorldDescription: Murder Drones Hub\n")
        f.write("//WorldCreator: MagmaMCNet\n\n")

        f.write(">> SECURITER > secu\n")
        for p in sorted(pseudos["SECURITER"]):
            f.write(f"{p}\n")
        f.write("\n")

        f.write(">> BAR > bar\n")
        for p in sorted(pseudos["BAR"]):
            f.write(f"{p}\n")
        f.write("\n")

        f.write(">> DJ > dj\n")
        for p in sorted(pseudos["DJ"]):
            f.write(f"{p}\n")
        f.write("\n")

        f.write(">> DIEUX > dj+bar+secu+spe\n")
        for p in sorted(pseudos["DIEUX"]):
            f.write(f"{p}\n")
        f.write("\n")

        f.write(">> ADMIN > dj+bar+secu\n")
        for p in sorted(pseudos["ADMIN"]):
            f.write(f"{p}\n")
        f.write("\n")

        f.write(">> BANNEDPLAYERS > Banned\n")
        for p in sorted(pseudos["BANNEDPLAYERS"]):
            f.write(f"{p}\n")

    # Après avoir écrit, on commit/push le fichier
    commit_and_push([WORLD_PERM_FILE], "Update WorldPermissions.PSC")

pseudos_list = charger_pseudos()

########################################
# DISCORD BOT
########################################

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

########################################
# OUTILS
########################################

def format_list() -> str:
    """Construit la liste des pseudos classés par catégorie."""
    total = sum(len(pseudos_list[c]) for c in CATEGORIES)
    if total == 0:
        return "❌ Aucun pseudo enregistré."

    txt = "📋 **Liste des pseudos enregistrés :**\n"
    for cat in CATEGORIES:
        data = sorted(pseudos_list[cat])
        if data:
            txt += f"\n**{cat}**\n" + "\n".join(f"• {p}" for p in data) + "\n"
    return txt

########################################
# COMMANDES
########################################

@bot.command()
async def ping(ctx):
    """Commande de test : !ping"""
    await ctx.send("Pong!")

@bot.command()
async def liste_pseudos(ctx):
    """Affiche la liste depuis WorldPermissions.PSC."""
    await ctx.send(format_list())

@bot.command()
async def supprimer_pseudo(ctx):
    """
    Propose un menu pour supprimer un pseudo.
    On ne supprime pas s'il est dans DIEUX.
    """
    nb_total = sum(len(pseudos_list[c]) for c in CATEGORIES)
    if nb_total == 0:
        await ctx.send("❌ Aucun pseudo à supprimer.")
        return

    class PseudoDropdown(discord.ui.Select):
        def __init__(self):
            opts = []
            for cat in CATEGORIES:
                for p in sorted(pseudos_list[cat]):
                    opts.append(discord.SelectOption(label=p, value=f"{cat}|{p}"))
            super().__init__(placeholder="Sélectionne un pseudo à supprimer", options=opts)

        async def callback(self, interaction: discord.Interaction):
            cat, pseudo = self.values[0].split("|")
            if cat == "DIEUX":
                await interaction.response.send_message(
                    "❌ Impossible de supprimer un pseudo de DIEUX.",
                    ephemeral=True
                )
                return

            pseudos_list[cat].discard(pseudo)
            sauvegarder_pseudos(pseudos_list)  # auto commit/push
            await interaction.response.send_message(
                f"🗑️ Pseudo `{pseudo}` supprimé de `{cat}` !",
                ephemeral=True
            )

    view = discord.ui.View()
    view.add_item(PseudoDropdown())
    await ctx.send("📋 Sélectionne un pseudo à supprimer :", view=view)

########################################
# UPLOAD/SHOW IMAGE
########################################

def save_and_push_image():
    """Commit/push l'image sfinx.png après écriture."""
    commit_and_push([IMAGE_PATH], "Update sfinx.png")

@bot.command()
async def upload_image(ctx):
    """
    Demande d'envoyer une image, la stocke en pub/sfinx.png,
    redimension 1431x1820, puis commit/push.
    """
    await ctx.send("📌 Envoie l'image dans ce salon (60s).")

    def check(m: discord.Message):
        return (
            m.author.id == ctx.author.id
            and m.channel.id == ctx.channel.id
            and len(m.attachments) > 0
        )

    try:
        msg = await bot.wait_for("message", check=check, timeout=60)
    except:
        await ctx.send("❌ Temps écoulé, réessaie la commande.")
        return

    att = msg.attachments[0]
    if not att.content_type or not att.content_type.startswith("image"):
        await ctx.send("❌ Le fichier envoyé n'est pas une image.")
        return

    os.makedirs("pub", exist_ok=True)
    await att.save(IMAGE_PATH)

    with Image.open(IMAGE_PATH) as im:
        im = im.resize((1431, 1820))
        im.save(IMAGE_PATH)

    # Commit/push l'image
    save_and_push_image()

    await ctx.send("✅ Image sfinx.png enregistrée (dans pub/) et push sur GitHub !")

@bot.command()
async def show_image(ctx):
    """Affiche pub/sfinx.png si elle existe, sinon message d'erreur."""
    if not os.path.exists(IMAGE_PATH):
        await ctx.send("❌ Aucune image n'est enregistrée.")
        return

    await ctx.send(file=discord.File(IMAGE_PATH))

########################################
# MENU !CONFIG
########################################

class CategoryDropdown(discord.ui.Select):
    """Permet d'ajouter un pseudo dans : SECURITER, BAR, DJ, ADMIN, BANNEDPLAYERS, pas DIEUX."""
    def __init__(self, pseudo: str):
        self.pseudo = pseudo
        allowed = [c for c in CATEGORIES if c != "DIEUX"]
        opts = []
        for cat in allowed:
            opts.append(discord.SelectOption(label=cat, description=cat.lower()))
        super().__init__(placeholder=f"Sélectionne un rôle pour {pseudo}", options=opts)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        pseudos_list[cat].add(self.pseudo)
        sauvegarder_pseudos(pseudos_list)  # commit/push
        await interaction.response.send_message(
            f"✅ Pseudo `{self.pseudo}` ajouté dans `{cat}` !",
            ephemeral=True
        )

class CategoryView(discord.ui.View):
    def __init__(self, pseudo: str):
        super().__init__()
        self.add_item(CategoryDropdown(pseudo))

class ConfigDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="📋 Voir la liste", value="liste"),
            discord.SelectOption(label="➕ Ajouter un pseudo", value="ajouter"),
            discord.SelectOption(label="❌ Supprimer un pseudo", value="supprimer"),
            discord.SelectOption(label="⬆️ Upload image", value="uploadimage"),
            discord.SelectOption(label="📷 Show image", value="showimage"),
        ]
        super().__init__(placeholder="Choisissez une option", options=options)

    async def callback(self, interaction: discord.Interaction):
        choix = self.values[0]

        if choix == "liste":
            await interaction.response.send_message(format_list(), ephemeral=True)

        elif choix == "ajouter":
            await interaction.response.send_message(
                "Tape le pseudo que tu veux ajouter (réponds ici).",
                ephemeral=True
            )
            def check(m: discord.Message):
                return m.author.id == interaction.user.id and m.channel.id == interaction.channel_id

            try:
                msg = await bot.wait_for("message", check=check, timeout=60)
            except:
                await interaction.followup.send("❌ Temps écoulé, réessaie.", ephemeral=True)
                return

            pseudo = msg.content.strip()
            if not pseudo:
                await interaction.followup.send("❌ Pseudo invalide.", ephemeral=True)
                return

            view = CategoryView(pseudo)
            await interaction.followup.send(
                f"Sélectionne la catégorie pour `{pseudo}` :",
                view=view,
                ephemeral=True
            )

        elif choix == "supprimer":
            nb_total = sum(len(pseudos_list[c]) for c in CATEGORIES)
            if nb_total == 0:
                await interaction.response.send_message("❌ Aucun pseudo à supprimer.", ephemeral=True)
                return

            class PseudoDropdown(discord.ui.Select):
                def __init__(self):
                    opts = []
                    for cat in CATEGORIES:
                        for p in sorted(pseudos_list[cat]):
                            opts.append(discord.SelectOption(label=p, value=f"{cat}|{p}"))
                    super().__init__(placeholder="Sélectionne un pseudo à supprimer", options=opts)

                async def callback(self, inter: discord.Interaction):
                    cat_p, p = self.values[0].split("|")
                    if cat_p == "DIEUX":
                        await inter.response.send_message(
                            "❌ Impossible de supprimer un pseudo de DIEUX.",
                            ephemeral=True
                        )
                        return

                    pseudos_list[cat_p].discard(p)
                    sauvegarder_pseudos(pseudos_list)  # commit/push
                    await inter.response.send_message(
                        f"🗑️ Pseudo `{p}` supprimé de `{cat_p}` !",
                        ephemeral=True
                    )

            v = discord.ui.View()
            v.add_item(PseudoDropdown())
            await interaction.response.send_message(
                "📋 Sélectionne un pseudo à supprimer :",
                view=v,
                ephemeral=True
            )

        elif choix == "uploadimage":
            await interaction.response.send_message(
                "Envoie l'image dans ce salon (60s).",
                ephemeral=True
            )
            def check(m: discord.Message):
                return (m.author.id == interaction.user.id and m.channel.id == interaction.channel_id and len(m.attachments) > 0)

            try:
                msg = await bot.wait_for("message", check=check, timeout=60)
            except:
                await interaction.followup.send("❌ Temps écoulé, réessaie.", ephemeral=True)
                return

            att = msg.attachments[0]
            if not att.content_type or not att.content_type.startswith("image"):
                await interaction.followup.send("❌ Le fichier envoyé n'est pas une image.", ephemeral=True)
                return

            os.makedirs("pub", exist_ok=True)
            await att.save(IMAGE_PATH)

            # redimension
            with Image.open(IMAGE_PATH) as im:
                im = im.resize((1431, 1820))
                im.save(IMAGE_PATH)

            # commit/push
            commit_and_push([IMAGE_PATH], "Update sfinx.png")

            await interaction.followup.send("✅ Image sauvegardée sous pub/sfinx.png (1431x1820) & push !", ephemeral=True)

        elif choix == "showimage":
            if not os.path.exists(IMAGE_PATH):
                await interaction.response.send_message("❌ Aucune image n'est enregistrée.", ephemeral=True)
            else:
                await interaction.response.send_message(
                    file=discord.File(IMAGE_PATH),
                    ephemeral=False
                )

class ConfigDropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ConfigDropdown())

@bot.command(name="config")
async def config_cmd(ctx):
    """Menu pour gérer WorldPermissions.PSC + pub/sfinx.png (commit/push auto)."""
    await ctx.send(
        "⚙️ **Configuration des rôles :**\nSélectionnez une option ci-dessous :",
        view=ConfigDropdownView()
    )

########################################
# EVENTS
########################################

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Commande inconnue. Utilisez `!help` pour voir les commandes disponibles.")
    else:
        raise error

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

bot.run(TOKEN)
