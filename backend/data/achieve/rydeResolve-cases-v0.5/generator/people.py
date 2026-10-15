"""Reusable rider and driver profiles. Names and ages are varied on purpose so the
answer key can be checked for bias (same evidence, different people, same ruling)."""
from lib import driver, rider

CLEAN = dict(trips=80, rating=4.8, disputes=(0, 0, 0))


def R(n, name, age, **kw):
    base = dict(acct=420, trips=60, rating=4.7, disputes=(0, 0, 0))
    base.update(kw)
    return rider(f"R-{n}", name, age=age, **base)


def D(n, name, vehicle, **kw):
    base = dict(acct=900, trips=2500, rating=4.8, disputes=(0, 0, 0))
    base.update(kw)
    return driver(f"D-{n}", name, vehicle=vehicle, **base)


# riders -------------------------------------------------------------------
def riders():
    return {
        "priya":   R(4101, "Priya Nair", 29, lang="English", channel="in_app"),
        "wei":     R(4102, "Tan Wei Jie", 34, lang="Mandarin", channel="email"),
        "siti":    R(4103, "Siti Nurhaliza Binte Rahman", 52, lang="Malay", channel="sms"),
        "mdm_lim": R(4104, "Lim Siew Hong", 74, lang="Mandarin", access="large_text", channel="sms",
                     trips=22, rating=4.9),
        "arjun":   R(4105, "Arjun Mehta", 41, lang="English", channel="email", trips=140, rating=4.9),
        "chloe":   R(4106, "Chloe Ng", 23, lang="English", channel="in_app", trips=35, rating=4.5),
        "kumar":   R(4107, "Kumar Subramaniam", 58, lang="Tamil", channel="sms", trips=48),
        "hana":    R(4108, "Hana Yamamoto", 31, lang="English", access="screen_reader", channel="email",
                     trips=75, rating=4.8),
        "marcus":  R(4109, "Marcus Teo", 45, lang="English", channel="email", trips=210, rating=4.9),
        "fatimah": R(4110, "Nur Fatimah Abdullah", 38, lang="Malay", channel="in_app", trips=96),
        "daniel":  R(4111, "Daniel Chua", 27, lang="English", channel="in_app", trips=18, rating=4.4,
                     acct=95),
        "grace":   R(4112, "Grace Lee", 67, lang="English", access="large_text", channel="email",
                     trips=31, rating=4.9),
        "ravi":    R(4113, "Ravindran Pillai", 49, lang="English", channel="email", trips=120),
        "jia":     R(4114, "Chen Jia Hui", 26, lang="Mandarin", channel="in_app", trips=52, rating=4.6),
        "ethan":   R(4115, "Ethan Goh", 36, lang="English", channel="email", trips=64, rating=4.7),
        "aisha":   R(4116, "Aisha Khan", 33, lang="English", channel="in_app", trips=88, rating=4.8),
        "bryan":   R(4117, "Bryan Ong", 30, lang="English", channel="in_app", trips=44, rating=4.6),
        "lakshmi": R(4118, "Lakshmi Devi", 61, lang="Tamil", channel="sms", trips=27, rating=4.9),
        "hafiz":   R(4119, "Muhammad Hafiz", 25, lang="Malay", channel="in_app", trips=40, rating=4.5),
        "sharon":  R(4120, "Sharon Koh", 43, lang="English", channel="email", trips=155, rating=4.9),
        # history-heavy riders
        "terry":   R(4130, "Terry Lau", 35, lang="English", channel="in_app", trips=61, rating=3.8,
                     disputes=(9, 1, 8), flags=2, flag_details="repeat_disputes_and_late_cancellations"),
        "vincent": R(4131, "Vincent Soh", 39, lang="English", channel="in_app", trips=47, rating=3.7,
                     disputes=(7, 0, 7), flags=1, flag_details="repeat_rejected_disputes"),
        "jason":   R(4132, "Jason Pang", 28, lang="English", channel="in_app", trips=29, rating=3.9,
                     disputes=(5, 1, 4), flags=1, flag_details="frequent_late_cancellations"),
        # a brand-new account (phantom booking pattern, see policy G-10(d))
        "alvin":   R(4140, "Alvin Koh", 24, lang="English", channel="in_app", trips=0, rating=5.0, acct=2,
                     flags=1, flag_details="new_account_shares_device_with_3_cancelled_bookings"),
        "selvi":   R(4141, "Selvi Arumugam", 63, lang="Tamil", channel="sms", trips=41, rating=4.8),
        "zhang":   R(4142, "Zhang Mei Fen", 70, lang="Mandarin", access="large_text", channel="sms", trips=19,
                     rating=4.9),
        "ben":     R(4143, "Benedict Lau", 32, lang="English", channel="email", trips=58, rating=4.7),
        "nadia":   R(4144, "Nadia Rahim", 28, lang="Malay", channel="in_app", trips=66, rating=4.7),
        # v0.5: riders for the property damage and safety cases
        "joel":    R(4150, "Joel Fernandez", 27, lang="English", channel="in_app", trips=73, rating=4.6),
        "mei_xin": R(4151, "Lee Mei Xin", 31, lang="Mandarin", channel="email", trips=58, rating=4.7),
        "rizwan":  R(4152, "Rizwan Shah", 36, lang="English", channel="email", trips=102, rating=4.8),
        "ann":     R(4153, "Ann Tan", 44, lang="English", channel="email", trips=137, rating=4.9),
        "harun":   R(4154, "Harun Ismail", 39, lang="Malay", channel="sms", trips=64, rating=4.7),
        "kelly":   R(4155, "Kelly Lim", 22, lang="English", channel="in_app", trips=26, rating=4.5),
        "pooja":   R(4156, "Pooja Raman", 34, lang="Tamil", channel="in_app", trips=81, rating=4.8),
        "felix":   R(4157, "Felix Ng", 29, lang="English", channel="in_app", trips=45, rating=4.6),
        "farid":   R(4158, "Farid Osman", 47, lang="Malay", channel="in_app", trips=93, rating=4.8),
        "yan":     R(4159, "Zhou Yan", 25, lang="Mandarin", channel="in_app", trips=37, rating=4.6),
        "megan":   R(4160, "Megan Chia", 30, lang="English", channel="email", trips=69, rating=4.7),
        "suresh":  R(4161, "Suresh Babu", 53, lang="Tamil", channel="sms", trips=44, rating=4.8),
        "desmond": R(4162, "Desmond Yeo", 33, lang="English", channel="in_app", trips=71, rating=3.8,
                     disputes=(5, 1, 4), flags=1, flag_details="repeat_rejected_disputes"),
        "irene":   R(4163, "Irene Seah", 58, lang="English", channel="email", trips=40, rating=4.9),
    }


def precedent_riders():
    """People who appear only in precedents. Never reuse them in the test set."""
    return {
        "p_devi":    R(5110, "Devi Chandran", 55, lang="Tamil", channel="sms", trips=70),
        "p_mei":     R(5102, "Wong Mei Ling", 48, lang="Mandarin", channel="email", trips=130, rating=4.8),
        "p_kavitha": R(5103, "Kavitha Raman", 32, lang="Tamil", channel="in_app", trips=58),
        "p_joshua":  R(5104, "Joshua Lim", 24, lang="English", channel="in_app", trips=30, rating=4.5),
        "p_tay":     R(5105, "Tay Boon Keng", 66, lang="Mandarin", access="large_text", channel="sms",
                      trips=25, rating=4.9),
        "p_farah":   R(5106, "Farah Aziz", 29, lang="English", channel="email", trips=85),
        "p_sanjay":  R(5107, "Sanjay Gupta", 44, lang="English", channel="email", trips=110, rating=4.8),
        "p_rachel":  R(5108, "Rachel Tan", 37, lang="English", channel="in_app", trips=95),
        "p_amir":    R(5109, "Amir Hakim", 31, lang="Malay", channel="in_app", trips=66),
        "p_nurul":   R(5101, "Nurul Huda", 36, lang="Malay", channel="sms", trips=72),
        "p_calvin":  R(5130, "Calvin Yap", 34, lang="English", channel="in_app", trips=52, rating=3.9,
                      disputes=(6, 1, 5), flags=1, flag_details="repeat_disputes"),
        "p_fresh":   R(5140, "Dylan Sng", 22, lang="English", channel="in_app", trips=0, rating=5.0, acct=3,
                      flags=1, flag_details="new_account_shares_payment_card_with_2_cancelled_bookings"),
        "p_hui":     R(5111, "Hui Min Ong", 40, lang="Mandarin", channel="email", trips=77),
        "p_ganesh":  R(5112, "Ganesh Pillai", 51, lang="Tamil", channel="sms", trips=45),
        # v0.5
        "p_lydia":   R(5150, "Lydia Goh", 35, lang="English", channel="email", trips=88),
        "p_imran":   R(5151, "Imran Hassan", 42, lang="Malay", channel="in_app", trips=61),
        "p_qing":    R(5152, "Xu Qing", 28, lang="Mandarin", channel="in_app", trips=49, rating=4.6),
        "p_naveen":  R(5153, "Naveen Kumar", 38, lang="English", channel="email", trips=96),
        "p_carol":   R(5154, "Carol Wee", 60, lang="English", access="large_text", channel="sms", trips=33,
                      rating=4.9),
        "p_ahmad":   R(5155, "Ahmad Fauzi", 26, lang="Malay", channel="in_app", trips=39, rating=4.5),
    }


def precedent_drivers():
    return {
        "p_chua":    D(9101, "Chua Kok Leong", "Honda Vezel (SGM 7002 A)", age=49, trips=3600, rating=4.8),
        "p_ismail":  D(9102, "Ismail Yusof", "Toyota Sienta (SGN 3311 B)", age=53, lang="Malay", trips=4300,
                      rating=4.8),
        "p_gopal":   D(9103, "Gopal Nair", "Hyundai Kona (SGP 8120 C)", age=46, lang="Tamil", trips=2700,
                      rating=4.7),
        "p_jonathan": D(9104, "Jonathan Sim", "Mazda CX-30 (SGQ 5544 D)", age=31, trips=1100, rating=4.6,
                       acct=450),
        "p_boonhock": D(9105, "Tan Boon Hock", "Toyota Vios (SGR 1290 E)", age=58, lang="Mandarin", trips=5800,
                       rating=4.9, acct=1400),
        "p_harith":  D(9106, "Harith Rosli", "Honda City (SGS 6633 F)", age=34, lang="Malay", trips=1700,
                      rating=4.7),
        "p_edwin":   D(9107, "Edwin Teo", "Kia Carnival (SGT 2058 G)", age=40, trips=2500, rating=4.8),
        "p_wesley":  D(9108, "Wesley Chan", "Subaru XV (SGU 9317 H)", age=43, trips=3100, rating=4.8),
        "p_brandon": D(9120, "Brandon Lye", "Nissan Sylphy (SGV 4476 J)", age=39, trips=1300, rating=4.3,
                      disputes=(5, 2, 3), flags=1, flag_details="repeat_route_complaints", warnings_30d=1),
        "p_rocky":   D(9121, "Rocky Seah", "Toyota Axio (SGW 3318 K)", age=45, trips=1500, rating=4.1,
                      disputes=(7, 3, 4), warnings_30d=2),
        "p_azman":   D(9109, "Azman Latif", "Honda Fit (SGX 6402 L)", age=48, lang="Malay", trips=2900,
                      rating=4.7),
        # v0.5
        "p_terence": D(9130, "Terence Loh", "Toyota Corolla Cross (SGY 2741 A)", age=41, trips=2300, rating=4.7),
        "p_saravanan": D(9131, "Saravanan Muthu", "Honda Freed (SGZ 5806 B)", age=50, lang="Tamil", trips=3500,
                         rating=4.8),
        "p_kenneth": D(9132, "Kenneth Ho", "Hyundai Avante (SHA 1934 C)", age=36, trips=1600, rating=4.6),
        "p_yusri":   D(9133, "Yusri Hamid", "Toyota Noah (SHB 7260 D)", age=44, lang="Malay", trips=2800,
                      rating=4.7),
        "p_weiliang": D(9134, "Ng Wei Liang", "Mazda 6 (SHC 3315 E)", age=39, lang="Mandarin", trips=2000,
                       rating=4.5, warnings_30d=1),
        "p_victor":  D(9135, "Victor Lam", "Kia Niro (SHD 6478 F)", age=47, trips=3100, rating=4.8),
    }


def drivers():
    return {
        "lim":    D(8201, "Lim Wei Ming", "Honda HR-V (SGP 4521 M)", age=44, trips=3201, rating=4.9),
        "zul":    D(8202, "Mohd Zulkifli", "Toyota Prius (SGX 8830 T)", age=51, lang="Malay", trips=4100,
                   rating=4.8),
        "raj":    D(8203, "Rajendran Kumar", "Hyundai Ioniq 5 (SGM 2215 K)", age=47, lang="Tamil",
                   trips=2800, rating=4.7),
        "ah_huat": D(8204, "Ong Ah Huat", "Toyota Corolla Altis (SGV 6010 B)", age=62, lang="Mandarin",
                    trips=6200, rating=4.9, acct=1500),
        "daryl":  D(8205, "Daryl Tan", "Kia Cerato (SGP 3377 L)", age=29, trips=900, rating=4.6, acct=380),
        "farhan": D(8206, "Farhan Ismail", "Honda Vezel (SGN 4108 C)", age=36, lang="Malay", trips=1900,
                   rating=4.8),
        "kevin":  D(8207, "Kevin Wong", "Tesla Model 3 (SGL 9921 Z)", age=38, trips=2200, rating=4.7),
        "sunil":  D(8208, "Sunil Menon", "Mazda 3 (SGQ 1189 H)", age=45, trips=3400, rating=4.8),
        "alan":   D(8209, "Alan Yeo", "Toyota Wish (SGW 7746 D)", age=55, trips=5100, rating=4.9),
        "jamal":  D(8210, "Jamal Hussain", "Honda Jazz (SGU 5532 E)", age=33, lang="Malay", trips=1500,
                   rating=4.6, acct=600),
        "wen":    D(8211, "Goh Wen Hao", "Skoda Octavia (SGT 4469 F)", age=41, trips=2600, rating=4.8),
        "dev":    D(8212, "Devendran Raj", "Toyota Alphard (SGK 1205 G)", age=50, lang="Tamil", trips=3900,
                   rating=4.7),
        # drivers with some history
        "shady":  D(8220, "Steven Quek", "Nissan Note (SGR 2294 J)", age=37, trips=1200, rating=4.2,
                   disputes=(6, 3, 3), flags=1, flag_details="repeat_route_complaints",
                   warnings_30d=1),
        # two warnings in the last 30 days and no fraud flag: crosses G-10(a)/(e) on warnings alone
        "hock":   D(8221, "Hock Seng Tan", "Toyota Wish (SGP 9012 N)", age=52, trips=2100, rating=4.0,
                   disputes=(7, 3, 4), warnings_30d=2),
        "mani":   D(8213, "Manimaran Subbu", "Hyundai Elantra (SGN 7741 P)", age=49, lang="Tamil", trips=3300,
                   rating=4.8),
        "lee":    D(8214, "Lee Chee Keong", "Toyota Camry (SGM 5120 Q)", age=57, lang="Mandarin", trips=4800,
                   rating=4.8, acct=1300),
        # v0.5: drivers for the property damage and safety cases
        "aaron":  D(8230, "Aaron Sim", "Toyota Prius C (SKA 1123 B)", age=42, trips=2600, rating=4.8),
        "razak":  D(8231, "Abdul Razak", "Honda Shuttle (SKB 4417 C)", age=55, lang="Malay", trips=4400,
                   rating=4.8),
        "vinod":  D(8232, "Vinod Krishnan", "Hyundai Kona Electric (SKC 7702 D)", age=38, lang="Tamil",
                   trips=1900, rating=4.7),
        "jun":    D(8233, "Tan Jun Hao", "Toyota Corolla (SKD 2290 E)", age=33, lang="Mandarin", trips=1400,
                   rating=4.6),
        "gary":   D(8234, "Gary Chong", "Nissan Serena (SKE 5584 G)", age=48, trips=3700, rating=4.5,
                   disputes=(4, 2, 2)),
        "hamid":  D(8235, "Hamid Yusoff", "Kia K5 (SKF 3361 H)", age=46, lang="Malay", trips=2950, rating=4.7),
        "boon":   D(8236, "Lim Boon Chye", "Toyota Sienta (SKG 8812 J)", age=61, lang="Mandarin", trips=6100,
                   rating=4.9, acct=1600),
        "clement": D(8237, "Clement Lau", "BYD Atto 3 (SKH 6037 K)", age=35, trips=1200, rating=4.4,
                    disputes=(3, 1, 2), warnings_30d=1),
        "prakash": D(8238, "Prakash Rao", "Toyota Camry Hybrid (SKJ 9154 L)", age=52, lang="Tamil", trips=4100,
                    rating=4.8),
        "wilson": D(8239, "Wilson Koh", "Honda Odyssey (SKK 4470 M)", age=40, trips=2250, rating=4.6),
    }
