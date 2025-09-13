import logging
import io
import os
import asyncio
import numpy as np
import matplotlib.pyplot as plt
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# --- Library Imports ---
from flask import Flask
from threading import Thread
import sqlalchemy
from sqlalchemy import create_engine, text

# --- Admin User ID ---
# Replace this with your own numeric Telegram User ID from @userinfobot
ADMIN_ID = 166949661

# --- Supabase (PostgreSQL) Database Connection ---
db_engine = None
try:
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        [span_0](start_span)print("Warning: DATABASE_URL not found. Stats will not be saved.")[span_0](end_span)
    else:
        if DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
        db_engine = create_engine(DATABASE_URL)
        # Create tables if they don't exist
        with db_engine.connect() as connection:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL
                );
            [span_1](start_span)"""))[span_1](end_span)
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            [span_2](start_span)"""))[span_2](end_span)
            connection.commit()
        print("Successfully connected to the database and tables are ready.")
except Exception as e:
    print(f"Error connecting to database: {e}")

# --- Keep-Alive Web Server ---
app = Flask('')
@app.route('/')
def home(): return "I'm alive!"
def run_flask(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Part 1: The Scientific Calculation Engine (Unchanged)
# ---------------------------------------------------------------------------
def get_rural_pasquill_gifford_params_c_d(stability_class):
    params = {'A':{'c':24.1670,'d':2.5334},'B':{'c':18.3330,'d':1.8096},'C':{'c':12.5000,'d':1.0857},'D':{'c':8.3330,'d':0.72382},'E':{'c':6.2500,'d':0.54287},'F':{'c':4.1667,'d':0.36191}}
    [span_3](start_span)return params.get(stability_class)[span_3](end_span)

def get_rural_sigma_z_params_a_b(stability_class, x_km):
    if stability_class == 'A':
        if x_km < 0.10: return {'a': 122.800, 'b': 0.94470}
        if 0.10 <= x_km <= 0.15: return {'a': 158.080, 'b': 1.05420}
        if 0.16 <= x_km <= 0.20: return {'a': 170.220, 'b': 1.09320}
        if 0.21 <= x_km <= 0.25: return {'a': 179.520, 'b': 1.12620}
        if 0.26 <= x_km <= 0.30: return {'a': 217.410, 'b': 1.26440}
        [span_4](start_span)if 0.31 <= x_km <= 0.40: return {'a': 258.890, 'b': 1.40940}[span_4](end_span)
        if 0.41 <= x_km <= 0.50: return {'a': 346.750, 'b': 1.72830}
        if 0.51 <= x_km <= 3.11: return {'a': 453.850, 'b': 2.11660}
        return None
    elif stability_class == 'B':
        if x_km < 0.20: return {'a': 90.673, 'b': 0.93198}
        [span_5](start_span)if 0.21 <= x_km <= 0.40: return {'a': 98.483, 'b': 0.98332}[span_5](end_span)
        return {'a': 109.300, 'b': 1.09710}
    elif stability_class == 'C': return {'a': 61.141, 'b': 0.91465}
    elif stability_class == 'D':
        if x_km < 0.30: return {'a': 34.459, 'b': 0.86974}
        if 0.31 <= x_km <= 1.00: return {'a': 32.093, 'b': 0.81066}
        if 1.01 <= x_km <= 3.00: return {'a': 32.093, 'b': 0.64403}
        [span_6](start_span)if 3.01 <= x_km <= 10.00: return {'a': 33.504, 'b': 0.60486}[span_6](end_span)
        if 10.01 <= x_km <= 30.00: return {'a': 36.650, 'b': 0.56589}
        return {'a': 44.053, 'b': 0.51179}
    elif stability_class == 'E':
        if x_km < 0.10: return {'a': 24.260, 'b': 0.83660}
        if 0.10 <= x_km <= 0.30: return {'a': 23.331, 'b': 0.81956}
        if 0.31 <= x_km <= 1.00: return {'a': 21.628, 'b': 0.75660}
        [span_7](start_span)if 1.01 <= x_km <= 2.00: return {'a': 21.628, 'b': 0.63077}[span_7](end_span)
        if 2.01 <= x_km <= 4.00: return {'a': 22.534, 'b': 0.57154}
        if 4.01 <= x_km <= 10.00: return {'a': 24.703, 'b': 0.50527}
        if 10.01 <= x_km <= 20.00: return {'a': 26.970, 'b': 0.46713}
        if 20.01 <= x_km <= 40.00: return {'a': 35.420, 'b': 0.37615}
        return {'a': 47.618, 'b': 0.29592}
    [span_8](start_span)elif stability_class == 'F':[span_8](end_span)
        if x_km < 0.20: return {'a': 15.209, 'b': 0.81558}
        if 0.21 <= x_km <= 0.70: return {'a': 14.457, 'b': 0.78407}
        if 0.71 <= x_km <= 1.00: return {'a': 13.953, 'b': 0.68465}
        if 1.01 <= x_km <= 2.00: return {'a': 13.953, 'b': 0.63227}
        if 2.01 <= x_km <= 3.00: return {'a': 14.823, 'b': 0.54503}
        [span_9](start_span)if 3.01 <= x_km <= 7.00: return {'a': 16.187, 'b': 0.46490}[span_9](end_span)
        if 7.01 <= x_km <= 15.00: return {'a': 17.836, 'b': 0.41507}
        if 15.01 <= x_km <= 30.00: return {'a': 22.651, 'b': 0.32681}
        if 30.01 <= x_km <= 60.00: return {'a': 27.074, 'b': 0.27436}
        return {'a': 34.219, 'b': 0.21716}
    return None

def calculate_concentration(
    x_receptor, y_receptor, z_receptor, Q_emission, u_ref, z_ref,
    stability_class, area_type, Hm_boundary_layer, ds_stack_diameter,
    hs_stack_height, Ts_stack_temp, Ta_ambient_temp, vs_stack_velocity,
    T_half_life
[span_10](start_span)):[span_10](end_span)
    trace_log = ""
    g = 9.8
    if x_receptor <= 0: return 0.0, "فاصله x باید مثبت باشد."
    p_exponent_map = {'rural':{'A':0.07,'B':0.07,'C':0.10,'D':0.15,'E':0.35,'F':0.55},'urban':{'A':0.15,'B':0.15,'C':0.20,'D':0.25,'E':0.30,'F':0.30}}
    p = p_exponent_map[area_type][stability_class]
    us = u_ref * (hs_stack_height / z_ref) ** p
    if us == 0: us = 1e-6
    [span_11](start_span)trace_log += "--- ۱. محاسبه سرعت باد در ارتفاع دودکش (Us) ---\n"[span_11](end_span)
    trace_log += f"با توجه به کلاس پایداری '{stability_class}' و نوع منطقه '{area_type}'، ضریب توان p={p:.2f} است.\n"
    trace_log += f"Us = U_ref * (hs / z_ref)^p\n"
    trace_log += f"Us = {u_ref} * ({hs_stack_height} / {z_ref})^{p:.2f} = {us:.2f} m/s\n\n"
    x_km = x_receptor / 1000.0
    [span_12](start_span)trace_log += f"--- ۲. محاسبه ضریب پراکندگی افقی (σy) برای x={x_receptor} متر ---\n"[span_12](end_span)
    if area_type == 'rural':
        params = get_rural_pasquill_gifford_params_c_d(stability_class)
        c, d = params['c'], params['d']
        theta = 0.017453293 * (c - d * np.log(x_km))
        sigma_y = 465.11628 * x_km * np.tan(theta)
        [span_13](start_span)trace_log += f"منطقه حومه‌ای (rural) انتخاب شد. ضرایب: c={c}, d={d}\n"[span_13](end_span)
        trace_log += f"σy = 465.11628 * x_km * tan(0.01745 * [c - d*ln(x_km)]) = {sigma_y:.2f} متر\n\n"
    else:
        factor = (1.0 + 0.0004 * x_receptor) ** -0.5
        if stability_class in ['A', 'B']: C_sy = 0.32
        elif stability_class == 'C': C_sy = 0.22
        elif stability_class == 'D': C_sy = 0.16
        else: C_sy = 0.11
        [span_14](start_span)sigma_y = C_sy * x_receptor * factor[span_14](end_span)
        [span_15](start_span)trace_log += f"منطقه شهری (urban) انتخاب شد. ضریب: C_sy={C_sy}\n"[span_15](end_span)
        trace_log += f"σy = {C_sy} * x * (1 + 0.0004*x)^-0.5 = {sigma_y:.2f} متر\n\n"
    [span_16](start_span)trace_log += f"--- ۳. محاسبه ضریب پراکندگی عمودی (σz) برای x={x_receptor} متر ---\n"[span_16](end_span)
    if area_type == 'rural':
        if stability_class == 'A' and x_km > 3.11:
            sigma_z = 5000.0
            trace_log += f"منطقه حومه‌ای (rural) و کلاس A با x > 3.11km -> σz = 5000 متر\n\n"
        else:
            params = get_rural_sigma_z_params_a_b(stability_class, x_km)
            [span_17](start_span)a, b = params['a'], params['b'][span_17](end_span)
            sigma_z = a * (x_km ** b)
            [span_18](start_span)trace_log += f"منطقه حومه‌ای (rural) انتخاب شد. ضرایب: a={a}, b={b}\n"[span_18](end_span)
            trace_log += f"σz = a * (x_km)^b = {sigma_z:.2f} متر\n"
        if stability_class in ['A', 'B', 'C'] and sigma_z > 5000:
            sigma_z = 5000.0
            trace_log += f"مقدار σz برای کلاس‌های A,B,C به 5000 متر محدود شد.\n\n"
        else:
            trace_log += "\n"
    [span_19](start_span)else:[span_19](end_span)
        if stability_class in ['A', 'B']: sigma_z = 0.24 * x_receptor * (1.0 + 0.001 * x_receptor) ** 0.5
        elif stability_class == 'C': sigma_z = 0.20 * x_receptor
        elif stability_class == 'D': sigma_z = 0.14 * x_receptor * (1.0 + 0.0003 * x_receptor) ** -0.5
        else: sigma_z = 0.08 * x_receptor * (1.0 + 0.0015 * x_receptor) ** -0.5
        [span_20](start_span)trace_log += f"منطقه شهری (urban) انتخاب شد.\n"[span_20](end_span)
        trace_log += f"مقدار محاسبه شده: σz = {sigma_z:.2f} متر\n\n"
    [span_21](start_span)trace_log += f"--- ۴. محاسبه ارتفاع موثر دودکش (he) ---\n"[span_21](end_span)
    delta_T = Ts_stack_temp - Ta_ambient_temp
    Fb = g * vs_stack_velocity * (ds_stack_diameter**2) * (delta_T / (4 * Ts_stack_temp))
    trace_log += f"گام ۴.۱: محاسبه پارامتر شناوری Fb = {Fb:.2f} m⁴/s³\n"
    is_stable = stability_class in ['E', 'F']
    stability_type = "پایدار" if is_stable else "ناپایدار"
    trace_log += f"گام ۴.۲: شرایط جوی '{stability_type}' تشخیص داده شد.\n"
    if is_stable:
        s = 0.035 if stability_class == 'F' else 0.020
        [span_22](start_span)delta_T_c = 0.01958 * Ts_stack_temp * vs_stack_velocity * np.sqrt(s)[span_22](end_span)
    else:
        if Fb >= 55: delta_T_c = 0.00575 * Ts_stack_temp * (vs_stack_velocity**(2/3)) / (ds_stack_diameter**(1/3))
        else: delta_T_c = 0.0297 * Ts_stack_temp * (vs_stack_velocity**(1/3)) / (ds_stack_diameter**(2/3))
    trace_log += f"گام ۴.۳: محاسبه دمای بحرانی ΔTc = {delta_T_c:.4f} K\n"
    is_buoyancy_dominated = delta_T > delta_T_c
    dom_phase = "شناوری غالب" if is_buoyancy_dominated else "تکانه غالب"
    [span_23](start_span)trace_log += f"گام ۴.۴: فاز '{dom_phase}' تشخیص داده شد (چون ΔT={delta_T:.2f}K در مقایسه با ΔTc={delta_T_c:.4f}K)\n"[span_23](end_span)
    if is_stable:
        s = 0.035 if stability_class == 'F' else 0.020
        if is_buoyancy_dominated: delta_h = 2.6 * (Fb / (us * s))**(1/3)
        else: delta_h = 3 * ds_stack_diameter * vs_stack_velocity / us
        xf = 2.075 * us / np.sqrt(s)
    else:
        if is_buoyancy_dominated:
            [span_24](start_span)if Fb >= 55:[span_24](end_span)
                [span_25](start_span)delta_h = 38.71 * (Fb**0.6) / us; xf = 119 * (Fb**0.4)[span_25](end_span)
            else:
                [span_26](start_span)delta_h = 21.25 * (Fb**0.75) / us; xf = 49 * (Fb**(5/8))[span_26](end_span)
        else:
            delta_h = 3 * ds_stack_diameter * vs_stack_velocity / us
            if Fb >= 55: xf = 119 * (Fb**0.4)
            else: xf = 49 * (Fb**(5/8))
    trace_log += f"گام ۴.۵: محاسبه خیز نهایی توده Δh = {delta_h:.2f} متر و فاصله آن xf = {xf:.2f} متر\n"
    [span_27](start_span)if vs_stack_velocity < 1.5 * us: h_prime_s = hs_stack_height + 2 * ds_stack_diameter * ((vs_stack_velocity / us) - 1.5)[span_27](end_span)
    else: h_prime_s = hs_stack_height
    trace_log += f"گام ۴.۶: محاسبه ارتفاع اصلاح شده دودکش (با Downwash) h's = {h_prime_s:.2f} متر\n"
    if x_receptor >= xf:
        he = h_prime_s + delta_h
        trace_log += f"گام ۴.۷: چون x >= xf، خیز نهایی استفاده شد. he = h's + Δh = {he:.2f} متر\n\n"
    else:
        [span_28](start_span)if is_buoyancy_dominated: he = h_prime_s + 1.6 * ((Fb * x_receptor**2) / us**3)**(1/3)[span_28](end_span)
        else:
            Fm = (vs_stack_velocity**2) * (ds_stack_diameter**2) * (Ta_ambient_temp / (4 * Ts_stack_temp))
            beta_j = (1/3) + (us / vs_stack_velocity)
            if is_stable: he = h_prime_s + 1.6 * ((Fm * x_receptor**2) / (beta_j**2 * us**2))**(1/3)
            [span_29](start_span)else: he = h_prime_s + ((3 * Fm * x_receptor) / (beta_j**2 * us**2))**(1/3)[span_29](end_span)
        [span_30](start_span)trace_log += f"گام ۴.۷: چون x < xf، از فرمول خیز تدریجی استفاده شد. he = {he:.2f} متر\n\n"[span_30](end_span)
    sigma_ye = np.sqrt(sigma_y**2 + (delta_h / 3.5)**2)
    sigma_ze = np.sqrt(sigma_z**2 + (delta_h / 3.5)**2)
    [span_31](start_span)trace_log += f"--- ۵. محاسبه ضرایب پراکندگی موثر ---\n"[span_31](end_span)
    trace_log += f"σye = (σy² + (Δh/3.5)²)^0.5 = {sigma_ye:.2f} متر\n"
    trace_log += f"σze = (σz² + (Δh/3.5)²)^0.5 = {sigma_ze:.2f} متر\n\n"
    if sigma_ze == 0: sigma_ze = 1e-6
    term1 = np.exp(-0.5 * ((z_receptor - he) / sigma_ze)**2)
    term2 = np.exp(-0.5 * ((z_receptor + he) / sigma_ze)**2)
    V = term1 + term2
    summation_term = 0
    for i in range(1, 6):
        H1 = z_receptor-(2*i*Hm_boundary_layer-he); H2=z_receptor+(2*i*Hm_boundary_layer-he)
        H3 = z_receptor-(2*i*Hm_boundary_layer+he); [span_32](start_span)H4=z_receptor+(2*i*Hm_boundary_layer+he)[span_32](end_span)
        summation_term += (np.exp(-0.5*(H1/sigma_ze)**2) + np.exp(-0.5*(H2/sigma_ze)**2) + np.exp(-0.5*(H3/sigma_ze)**2) + np.exp(-0.5*(H4/sigma_ze)**2))
    V += summation_term
    [span_33](start_span)trace_log += f"--- ۶. محاسبه جمله قائم (V) ---\n"[span_33](end_span)
    trace_log += f"با در نظر گرفتن انعکاس از زمین و لایه مرزی، V = {V:.4f}\n\n"
    [span_34](start_span)trace_log += f"--- ۷. محاسبه جمله زوال (D) ---\n"[span_34](end_span)
    if T_half_life > 0:
        psi = 0.693 / T_half_life
        D = np.exp(-psi * x_receptor / us)
        trace_log += f"با نیمه عمر {T_half_life} ثانیه، ضریب زوال ψ = {psi:.4e}\n"
        trace_log += f"مقدار D = exp(-ψ * x / Us) = {D:.4f}\n\n"
    else:
        D = 1.0
        [span_35](start_span)trace_log += f"آلاینده پایدار فرض شد (نیمه عمر=0)، D = 1.0\n\n"[span_35](end_span)
    [span_36](start_span)trace_log += f"--- ۸. محاسبه غلظت نهایی (C) ---\n"[span_36](end_span)
    K = 1e6
    if sigma_ye == 0: sigma_ye = 1e-6
    lateral_term = np.exp(-0.5 * (y_receptor / sigma_ye)**2)
    denominator = 2 * np.pi * us * sigma_ye * sigma_ze
    if denominator == 0: return np.inf, trace_log
    C = (Q_emission * K * V * D / denominator) * lateral_term
    trace_log += f"C = (Q*K*V*D) / (2*π*Us*σye*σze) * exp[-0.5*(y/σye)²]\n"
    trace_log += f"C = ({Q_emission}*{K:.0f}*{V:.2f}*{D:.2f})/(2*π*{us:.2f}*{sigma_ye:.2f}*{sigma_ze:.2f})*exp[-0.5*({y_receptor}/{sigma_ye:.2f})²]\n"
    return C, trace_log

def generate_plot_for_telegram(params, single_point_coords):
    [span_37](start_span)grid_resolution=80; x_max_m=10000; y_max_m=2000[span_37](end_span)
    x_points=np.linspace(1,x_max_m,grid_resolution); y_points=np.linspace(-y_max_m,y_max_m,grid_resolution)
    X, Y = np.meshgrid(x_points, y_points)
    Z = np.zeros_like(X)
    plot_height_z = single_point_coords['z']
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            conc, _ = calculate_concentration(x_receptor=X[i,j], y_receptor=Y[i,j], z_receptor=plot_height_z, **params)
            Z[i, j] = conc
    fig, ax = plt.subplots(figsize=(10, 7))
    contour = ax.pcolormesh(X, Y, Z, cmap='jet', shading='auto', vmin=0)
    [span_38](start_span)cbar = fig.colorbar(contour, ax=ax)[span_38](end_span)
    cbar.set_label('Concentration (μg/m³)')
    ax.plot(single_point_coords['x'], single_point_coords['y'], 'w+', markersize=10, label=f"User's Point")
    ax.legend()
    ax.set_title(f'Pollutant Concentration Distribution at Z = {plot_height_z} m')
    ax.set_xlabel('Downwind Distance (m)')
    ax.set_ylabel('Crosswind Distance (m)')
    buf = io.BytesIO()
    plt.savefig(buf, format='PNG')
    buf.seek(0)
    plt.close(fig)
    return buf

# ---------------------------------------------------------------------------
# Part 2: Telegram Bot Implementation
# ---------------------------------------------------------------------------
(GET_X, GET_Y, GET_Z, GET_Q, GET_U_REF, GET_Z_REF, GET_STABILITY, GET_AREA, GET_HM,
 GET_DS, GET_HS, GET_TS, GET_TA, GET_VS_CHOICE, GET_VS, GET_QS, GET_HALF_LIFE) = range(17)
[span_39](start_span)MAIN_MENU_KEYBOARD = [["محاسبات ⚙️"], ["آموزش و بررسی کد ربات 📚"], ["لینک پروژه در گیت هاب 🔗"]][span_39](end_span)
MAIN_MENU_MARKUP = ReplyKeyboardMarkup(MAIN_MENU_KEYBOARD, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if db_engine:
        try:
            with db_engine.connect() as connection:
                user_exists_query = text("SELECT 1 FROM users WHERE user_id = :user_id")
                [span_40](start_span)result = connection.execute(user_exists_query, {"user_id": user.id}).first()[span_40](end_span)
                if not result:
                    add_user_query = text("INSERT INTO users (user_id) VALUES (:user_id)")
                    connection.execute(add_user_query, {"user_id": user.id})
                    connection.commit()
        except Exception as e:
            [span_41](start_span)logger.error(f"Error updating user stats: {e}")[span_41](end_span)
    welcome_message = (
        "به نام خدا\n"
        "من یک ربات مدل سازی آلودگی هوا و کاملا ایرانی هستم🇮🇷\n"
        "من توسط محمدامین فاطمی مهر دانشجو کارشناسی ارشد دانشگاه تهران رشته سیستم های محیط زیست "
        "برای درس مدل سازی آلودگی هوا که توسط جناب آقای دکتر اشرفی تدریس شده است ، "
        [span_42](start_span)"بر پایه پایتون توسعه داده شده ام.[span_42](end_span) [span_43](start_span)کلیه الگوریتم استفاده شده برای کدنویسی من طبق "[span_43](end_span)
        "فصل پنج جزوه دکتر اشرفی تهیه و آماده شده است.\n"
        "امیدوارم با استفاده از ایده طراحی من با زیبایی های درس مدل سازی آلودگی هوا "
        "بیشتر آشنا شده و از آن بهره مند شوید.😊☁️\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await update.message.reply_text(welcome_message, reply_markup=MAIN_MENU_MARKUP)

async def show_github_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "این ربات یک پروژه متن‌باز است. برای مشاهده و بررسی کدها می‌توانید به لینک زیر در گیت‌هاب مراجعه کنید:\n"
        "https://github.com/fatemimehr/air-quality-bot",
        reply_markup=MAIN_MENU_MARKUP
    [span_44](start_span))

# -------------------------------------------------------------------------------------
# --- START OF MODIFIED SECTION: Tutorial for the Scientific Code (SimpleCode) ---
# -------------------------------------------------------------------------------------
async def show_code_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provides a detailed, step-by-step tutorial on the Gaussian model calculation logic."""
    await update.message.reply_text(
        "📚 **آموزش جامع موتور علمی ربات (مدل گوسی)** 📚\n\n"
        "سلام! در ادامه، قلب تپنده این ربات، یعنی تابع `calculate_concentration` را که مسئول تمام محاسبات علمی است، به صورت گام به گام بررسی می‌کنیم.",
        reply_markup=MAIN_MENU_MARKUP
    )
    await asyncio.sleep(2)

    await update.message.reply_text(
        "**مقدمه: مدل پراکندگی گوسی**\n\n"
        "این مدل فرض می‌کند که توده آلاینده خارج شده از دودکش، در حین حرکت در راستای باد، در جهت‌های افقی و عمودی پراکنده می‌شود. توزیع غلظت در هر مقطع عمود بر باد، شبیه به توزیع نرمال یا زنگوله‌ای (گوسی) است. هدف ما محاسبه غلظت در یک نقطه مشخص (x, y, z) است."
    )
    await asyncio.sleep(2.5)

    await update.message.reply_text(
        "**گام اول: محاسبه سرعت باد در ارتفاع دودکش (Us)** 💨\n\n"
        "سرعت باد با افزایش ارتفاع از سطح زمین تغییر می‌کند. ما با استفاده از 'پروفایل توانی باد'، سرعت باد مرجع (u_ref) که در ارتفاع z_ref اندازه‌گیری شده را به سرعت باد در ارتفاع نوک دودکش (hs) تبدیل می‌کنیم.\n\n"
        "فرمول:\n"
        "`Us = u_ref * (hs / z_ref) ^ p`\n\n"
        "که در آن `p` یک ضریب توانی است که به پایداری جو و نوع منطقه (شهری/حومه‌ای) بستگی دارد."
    )
    await asyncio.sleep(2.5)

    await update.message.reply_text(
        "**گام دوم: محاسبه ضرایب پراکندگی (σy و σz)** 📏\n\n"
        "این دو پارامتر کلیدی، میزان پخش‌شدگی توده آلاینده را در جهت افقی (σy) و عمودی (σz) نشان می‌دهند. مقدار آن‌ها به شدت به 'کلاس پایداری جو' (از A: بسیار ناپایدار تا F: بسیار پایدار) و فاصله از منبع (x) بستگی دارد.\n\n"
        "این مقادیر از جداول و فرمول‌های تجربی 'پاسکوئیل-گیفورد' به دست می‌آیند که در توابع `get_rural_pasquill_gifford_params_c_d` و `get_rural_sigma_z_params_a_b` پیاده‌سازی شده‌اند."
    )
    await asyncio.sleep(2.5)

    await update.message.reply_text(
        "**گام سوم: محاسبه ارتفاع موثر دودکش (he)** 🗼\n\n"
        "این یکی از مهم‌ترین بخش‌های مدل است. ارتفاع موثر برابر با ارتفاع فیزیکی دودکش (`hs`) به علاوه میزان صعود توده آلاینده (`Δh`) پس از خروج است.\n\n"
        "`he = hs + Δh`\n\n"
        "محاسبه `Δh` (خیز توده) پیچیده است و به دو عامل اصلی بستگی دارد:\n"
        "1.  **شناوری (Buoyancy):** ناشی از اختلاف دمای گاز خروجی با هوای محیط.\n"
        "2.  **تکانه (Momentum):** ناشی از سرعت خروج گاز از دهانه دودکش.\n\n"
        "کد ابتدا تشخیص می‌دهد که کدام یک از این دو فاز (شناوری یا تکانه) غالب است و بر اساس شرایط جوی (پایدار یا ناپایدار)، از فرمول‌های مربوطه برای محاسبه خیز نهایی توده استفاده می‌کند."
    )
    await asyncio.sleep(2.5)

    await update.message.reply_text(
        "**گام چهارم: معادله نهایی گوسی** 🧮\n\n"
        "در نهایت، تمام پارامترهای محاسبه‌شده در معادله اصلی گوسی قرار می‌گیرند تا غلظت نهایی (C) به دست آید:\n\n"
        "`C = (Q*K*V*D) / (2*π*Us*σye*σze) * exp[-0.5*(y/σye)²]`\n\n"
        "اجزای اصلی فرمول:\n"
        "▫️ `Q`: نرخ انتشار آلاینده (ورودی کاربر)\n"
        "▫️ `V` (جمله قائم): این بخش اثر انعکاس توده از سطح زمین و لایه مرزی بالایی را مدل می‌کند.\n"
        "▫️ `D` (جمله زوال): اگر آلاینده ناپایدار باشد (نیمه‌عمر > 0)، این جمله کاهش غلظت آن در طول مسیر را محاسبه می‌کند.\n"
        "▫️ `exp[...]` (جمله پخش جانبی): توزیع گوسی غلظت در راستای محور y را مدل می‌کند."
    )
    await asyncio.sleep(2)

    await update.message.reply_text(
        "آموزش بخش علمی کد به پایان رسید. امیدوارم مفید بوده باشد! 😊"
    )
# -----------------------------------------------------------------------------------
# --- END OF MODIFIED SECTION ---
# -----------------------------------------------------------------------------------

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id == ADMIN_ID:
        if not db_engine:
            await update.message.reply_text("خطا: اتصال به پایگاه داده آمار برقرار نیست.")
            return
        try:
            with db_engine.connect() as connection:
                user_count_query = text("SELECT count(*) FROM users")[span_44](end_span)
                total_users = connection.execute(user_count_query).scalar_one() or 0

                calc_count_query = text("SELECT value FROM stats WHERE key = 'calculation_count'")
                calc_count_result = connection.execute(calc_count_query).first()
                [span_45](start_span)calc_count = int(calc_count_result[0]) if calc_count_result else 0[span_45](end_span)

                stats_message = (
                    f"📊 **آمار استفاده از ربات**\n\n"
                    f"تعداد کاربران یکتا: **{total_users}** نفر\n"
                    [span_46](start_span)f"تعداد کل محاسبات انجام شده: **{calc_count}** بار"[span_46](end_span)
                )
                await update.message.reply_text(stats_message, parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"خطا در خواندن آمار از پایگاه داده: {e}")
    else:
        await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")

# (Conversation handler functions are complete and included below)
[span_47](start_span)async def calculate_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:[span_47](end_span)
    context.user_data.clear()
    [span_48](start_span)await update.message.reply_text("شروع فرآیند محاسبه. لطفاً ۱۵ پارامتر زیر را به ترتیب وارد کنید.\n"[span_48](end_span)
                                "برای لغو عملیات در هر مرحله، دستور /cancel را ارسال کنید.\n\n"
                                [span_49](start_span)"۱. لطفاً فاصله در راستای باد (x) را به متر وارد کنید:", reply_markup=ReplyKeyboardRemove())[span_49](end_span)
    return GET_X
async def get_x(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['x'] = float(update.message.text)
        await update.message.reply_text("۲. فاصله عرضی از محور باد (y) به متر:")
        return GET_Y
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        return GET_X
[span_50](start_span)async def get_y(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:[span_50](end_span)
    try:
        context.user_data['y'] = float(update.message.text)
        await update.message.reply_text("۳. ارتفاع گیرنده از سطح زمین (z) به متر:")
        return GET_Z
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        return GET_Y
async def get_z(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['z'] = float(update.message.text)
        [span_51](start_span)await update.message.reply_text("۴. نرخ انتشار آلاینده (Q) به گرم بر ثانیه:")[span_51](end_span)
        return GET_Q
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        return GET_Z
async def get_q(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['Q_emission'] = float(update.message.text)
        await update.message.reply_text("۵. سرعت باد مرجع (u_ref) به متر بر ثانیه:")
        return GET_U_REF
    [span_52](start_span)except ValueError:[span_52](end_span)
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        return GET_Q
async def get_u_ref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['u_ref'] = float(update.message.text)
        await update.message.reply_text("۶. ارتفاع مرجع (z_ref) به متر:")
        return GET_Z_REF
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        [span_53](start_span)return GET_U_REF[span_53](end_span)
async def get_z_ref(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['z_ref'] = float(update.message.text)
        reply_keyboard = [['A', 'B', 'C'], ['D', 'E', 'F']]
        [span_54](start_span)await update.message.reply_text("۷. کلاس پایداری جو را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))[span_54](end_span)
        return GET_STABILITY
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        return GET_Z_REF
async def get_stability(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.upper()
    if user_input in ['A', 'B', 'C', 'D', 'E', 'F']:
        context.user_data['stability_class'] = user_input
        reply_keyboard = [['urban', 'rural']]
        [span_55](start_span)await update.message.reply_text("۸. نوع منطقه را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))[span_55](end_span)
        return GET_AREA
    else:
        await update.message.reply_text("انتخاب نامعتبر. لطفاً یکی از دکمه‌ها را انتخاب کنید.")
        return GET_STABILITY
async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text.lower()
    if user_input in ['urban', 'rural']:
        context.user_data['area_type'] = user_input
        [span_56](start_span)await update.message.reply_text("۹. ارتفاع لایه مرزی (Hm) به متر:", reply_markup=ReplyKeyboardRemove())[span_56](end_span)
        return GET_HM
    else:
        await update.message.reply_text("انتخاب نامعتبر. لطفاً 'urban' یا 'rural' را انتخاب کنید.")
        return GET_AREA
async def get_hm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['Hm_boundary_layer'] = float(update.message.text)
        await update.message.reply_text("۱۰. قطر داخلی دودکش (ds) به متر:")
        return GET_DS
    except ValueError:
        [span_57](start_span)await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")[span_57](end_span)
        return GET_HM
async def get_ds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['ds_stack_diameter'] = float(update.message.text)
        await update.message.reply_text("۱۱. ارتفاع فیزیکی دودکش (hs) به متر:")
        return GET_HS
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        return GET_DS
[span_58](start_span)async def get_hs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:[span_58](end_span)
    try:
        context.user_data['hs_stack_height'] = float(update.message.text)
        [span_59](start_span)await update.message.reply_text("۱۲. دمای گاز خروجی (Ts) به کلوین:")[span_59](end_span)
        return GET_TS
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")
        return GET_HS
async def get_ts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['Ts_stack_temp'] = float(update.message.text)
        await update.message.reply_text("۱۳. دمای هوای محیط (Ta) به کلوین:")
        return GET_TA
    except ValueError:
        [span_60](start_span)await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")[span_60](end_span)
        return GET_TS
async def get_ta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['Ta_ambient_temp'] = float(update.message.text)
        reply_keyboard = [['vs', 'qs']]
        await update.message.reply_text("۱۴. سرعت خروج گاز (vs) یا دبی (qs) را وارد می‌کنید؟", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return GET_VS_CHOICE
    except ValueError:
        [span_61](start_span)await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")[span_61](end_span)
        return GET_TA
async def get_vs_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.lower()
    if choice == 'vs':
        await update.message.reply_text("لطفاً سرعت خروج (vs) به متر بر ثانیه را وارد کنید:", reply_markup=ReplyKeyboardRemove())
        return GET_VS
    elif choice == 'qs':
        await update.message.reply_text("لطفاً دبی (qs) به متر مکعب بر ثانیه را وارد کنید:", reply_markup=ReplyKeyboardRemove())
        return GET_QS
    [span_62](start_span)else:[span_62](end_span)
        await update.message.reply_text("انتخاب نامعتبر. لطفاً 'vs' یا 'qs' را انتخاب کنید.")
        return GET_VS_CHOICE
async def get_vs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['vs_stack_velocity'] = float(update.message.text)
        await update.message.reply_text("۱۵. و در آخر، نیمه عمر آلاینده (T1/2) به ثانیه (برای آلاینده پایدار 0 وارد کنید):")
        return GET_HALF_LIFE
    except ValueError:
        [span_63](start_span)await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد صحیح وارد کنید.")[span_63](end_span)
        return GET_VS
async def get_qs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        qs = float(update.message.text)
        ds = context.user_data['ds_stack_diameter']
        vs = (4 * qs) / (np.pi * ds**2)
        context.user_data['vs_stack_velocity'] = vs
        await update.message.reply_text(
            f"سرعت خروج گاز محاسبه شد: {vs:.2f} m/s\n\n"
            [span_64](start_span)"۱۵. و در آخر، نیمه عمر آلاینده (T1/2) به ثانیه (برای آلاینده پایدار 0 وارد کنید):"[span_64](end_span)
        )
        return GET_HALF_LIFE
    except (ValueError, KeyError):
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد برای دبی وارد کنید.")
        return GET_QS
async def get_half_life_and_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['T_half_life'] = float(update.message.text)
    [span_65](start_span)except ValueError:[span_65](end_span)
        await update.message.reply_text("ورودی نامعتبر است. لطفاً یک عدد برای نیمه عمر وارد کنید.")
        return GET_HALF_LIFE
    [span_66](start_span)await update.message.reply_text("تمام ورودی‌ها دریافت شد. لطفاً برای انجام محاسبات صبر کنید...", reply_markup=ReplyKeyboardRemove())[span_66](end_span)
    single_point_coords = {'x': context.user_data.pop('x'), 'y': context.user_data.pop('y'), 'z': context.user_data.pop('z')}
    scenario_params = context.user_data
    scenario_params.pop('current_state', None)

    if db_engine:
        try:
            with db_engine.connect() as connection:
                upsert_query = text("""
                    INSERT INTO stats (key, value) VALUES ('calculation_count', '1')
                    ON CONFLICT (key) DO UPDATE SET value = (SELECT (value::integer + 1)::text FROM stats WHERE key = 'calculation_count');
                [span_67](start_span)""")[span_67](end_span)
                connection.execute(upsert_query)
                connection.commit()
        except Exception as e:
            [span_68](start_span)logger.error(f"Error updating calculation stats: {e}")[span_68](end_span)

    concentration, trace_report = calculate_concentration(
        x_receptor=single_point_coords['x'], y_receptor=single_point_coords['y'], z_receptor=single_point_coords['z'],
        **scenario_params
    )
    await update.message.reply_text(f"📝 **گزارش گام به گام محاسبات:**\n\n`{trace_report}`", parse_mode='Markdown')
    await update.message.reply_text(
        f"✅ **نتیجه نهایی**\n\n"
        f"غلظت محاسبه شده در نقطه (x={single_point_coords['x']}, y={single_point_coords['y']}, z={single_point_coords['z']}) برابر است با:\n"
        [span_69](start_span)f"**{concentration:.4f} میکروگرم بر متر مکعب**"[span_69](end_span)
    , parse_mode='Markdown')
    await update.message.reply_text("در حال آماده‌سازی نمودار... این مرحله ممکن است کمی طول بکشد.")
    plot_buffer = generate_plot_for_telegram(scenario_params, single_point_coords)
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=plot_buffer, caption="Pollutant concentration diagram.")
    [span_70](start_span)await update.message.reply_text("محاسبه کامل شد! برای بازگشت به منوی اصلی، دستور /start را ارسال کنید.", reply_markup=MAIN_MENU_MARKUP)[span_70](end_span)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("عملیات لغو شد. شما به منوی اصلی بازگشتید.", reply_markup=MAIN_MENU_MARKUP)
    return ConversationHandler.END

def main() -> None:
    keep_alive()
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found in Render Secrets.")
        return
    application = Application.builder().token(TOKEN).build()

    [span_71](start_span)conv_handler = ConversationHandler([span_71](end_span)
        entry_points=[
            CommandHandler("calculate", calculate_start),
            MessageHandler(filters.Regex('^محاسبات ⚙️$'), calculate_start)
        ],
        states={
            GET_X: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_x)],
            GET_Y: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_y)],
            [span_72](start_span)GET_Z: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_z)],[span_72](end_span)
            GET_Q: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_q)],
            GET_U_REF: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_u_ref)],
            GET_Z_REF: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_z_ref)],
            GET_STABILITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_stability)],
            GET_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_area)],
            [span_73](start_span)GET_HM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hm)],[span_73](end_span)
            GET_DS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ds)],
            GET_HS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_hs)],
            GET_TS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ts)],
            GET_TA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ta)],
            GET_VS_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vs_choice)],
            GET_VS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_vs)],
            [span_74](start_span)GET_QS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_qs)],[span_74](end_span)
            GET_HALF_LIFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_half_life_and_run)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex('^آموزش و بررسی کد ربات 📚$'), show_code_tutorial))
    application.add_handler(MessageHandler(filters.Regex('^لینک پروژه در گیت هاب 🔗$'), show_github_link))
    application.add_handler(CommandHandler("stats", stats))

    print("Bot is running...")
    application.run_polling()

[span_75](start_span)if __name__ == "__main__":[span_75](end_span)
    main()
