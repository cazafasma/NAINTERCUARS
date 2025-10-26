#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, math, random, statistics, sys
from datetime import datetime

# ---------- Utilidades ----------
def clamp(v, lo, hi): 
    return max(lo, min(hi, v))

def softplus(x): 
    return math.log1p(math.exp(x))

# ---------- “Stockfish” sintético (eval flotante con compensaciones) ----------
def stockfish_eval(position, move, game_phase, difficulty):
    # valores base
    material = position["material"] / 7.0
    mobility  = math.sqrt(max(position["mobility"], 1)) / math.sqrt(7)
    control   = position["control"] / 100.0
    ev = material + mobility + control + (position["mobility"] / 10.0)

    if difficulty in ("HARD", "VERY_HARD"):
        if game_phase == "OPENING":   ev *= 1.05
        elif game_phase == "MIDDLEGAME": ev *= 1.10
        else: ev *= 1.15
        ev += (position["material"] % 100) / 1000.0  # heurística fina

    if difficulty == "VERY_HARD":
        ev += math.sin(position["control"] / 30.0) * 0.5  # patrón táctico
        ev += (move * 0.0001)                              # ligera “memoria”

    # ruido flotante controlado (dificultad mayor => menos error)
    noise = {"NORMAL": 0.25, "HARD": 0.18, "VERY_HARD": 0.12}[difficulty]
    ev += random.uniform(-noise, noise)

    # sesgo para que no sea “perfecto”
    ev += (move * 0.00001) * (1.0 / 7.0)
    ev += math.sqrt(move) / math.sqrt(7) * 0.0001

    return ev

# ---------- Evaluación Modular (exacta) ----------
def modular_eval(position, move, mode, prev_mode, consecutive_same_mode):
    # valor bruto “entero”
    valor = position["material"] * 100
    valor += position["mobility"] * 10
    valor += position["control"]
    valor += move * 13       # primo para movimiento
    if prev_mode != mode:
        valor += 17          # cambio de estrategia
    if consecutive_same_mode > 5:
        valor -= consecutive_same_mode * 7  # penaliza atasco

    mod7  = valor % 7
    mod10 = valor % 10

    if mode == "PENSAR":
        suma = mod7 + mod10
        # patrón especial
        if mod7 == 6 and mod10 >= 8:
            return suma + 3
        return suma
    else:  # ATACAR
        producto = mod7 * mod10
        if producto >= 40: 
            return producto + 5  # táctica fuerte
        if producto == 0: 
            return 0             # neutra
        return producto

# ---------- Generar posición pseudo-realista ----------
def generate_position(move_number, prev=None):
    phase = "OPENING" if move_number < 15 else ("MIDDLEGAME" if move_number < 40 else "ENDGAME")
    if prev:
        material = prev["material"] + (random.random() - 0.5) * 100
        mobility = prev["mobility"] + (random.random() - 0.5) * 10
        control  = prev["control"]  + (random.random() - 0.5) * 20
    else:
        material = random.randint(500, 1500)
        mobility = random.randint(10, 60)
        control  = random.randint(0, 100)

    material = int(clamp(material, 200, 2000))
    mobility = int(clamp(mobility, 5, 60))
    control  = int(clamp(control, 0, 100))

    return {"material": material, "mobility": mobility, "control": control, "moveNumber": move_number, "phase": phase}

# ---------- Decidir modo (PENSAR/ATACAR) ----------
def decide_mode(position, prev_mode, eval_hist):
    mobility, control, phase = position["mobility"], position["control"], position["phase"]
    should_attack = False
    if len(eval_hist) >= 3:
        recent = eval_hist[-3:]
        improving = all(i == 0 or recent[i]["modEval"] >= recent[i-1]["modEval"] for i in range(len(recent)))
        if improving and phase != "OPENING":
            should_attack = True

    if control > 70 and mobility > 35: return "ATACAR"
    if control < 30 and mobility < 20: return "PENSAR"
    if phase == "OPENING": return "PENSAR"
    if phase == "ENDGAME" and mobility > 25: return "ATACAR"
    if prev_mode == "PENSAR" and mobility > 30: return "ATACAR"
    if prev_mode == "ATACAR" and control < 40: return "PENSAR"
    return "ATACAR" if should_attack else "PENSAR"

# ---------- Detectar hueco explotable ----------
def detect_hueco(mod_eval, sf_eval, mode):
    sf_round = round(sf_eval * 10)
    diff = abs(mod_eval - sf_round)
    if mode == "ATACAR" and diff > 8:  return True, diff
    if mode == "PENSAR" and diff > 5:  return True, diff
    return False, diff

# ---------- Simular una partida ----------
def simulate_game(difficulty):
    moves = 35 + random.randint(0, 30)  # 35-65
    mod_score = 0.0
    sf_score  = 0.0
    move_hist = []
    eval_hist = []
    prev_mode = "PENSAR"
    same = 0
    prev_pos = None

    for mv in range(1, moves + 1):
        pos = generate_position(mv, prev_pos)
        mode = decide_mode(pos, prev_mode, eval_hist)
        same = same + 1 if mode == prev_mode else 1

        mod_ev = modular_eval(pos, mv, mode, prev_mode, same)
        sf_ev  = stockfish_eval(pos, mv, pos["phase"], difficulty)
        detected, gap = detect_hueco(mod_ev, sf_ev, mode)

        mod_adv = 0.0
        sf_adv  = 0.0
        if detected:
            if mode == "ATACAR" and gap > 10:   mod_adv += 4.0
            elif mode == "PENSAR" and gap > 6:  mod_adv += 2.0
            elif gap > 8:                        mod_adv += 1.5

        if mode == "ATACAR" and mod_ev >= 35: mod_adv += 1.5
        if mode == "PENSAR" and mod_ev >= 12: mod_adv += 1.0

        if difficulty in ("HARD", "VERY_HARD"):
            if pos["phase"] == "MIDDLEGAME": sf_adv += 0.8
            if pos["control"] > 60 and pos["mobility"] > 30: sf_adv += 1.0
            if mv > 20 and difficulty == "VERY_HARD": mod_adv *= 0.85

        sf_error = abs(sf_ev - round(sf_ev))
        if sf_error > 0.4: mod_adv += 0.5
        else:              sf_adv  += 0.3

        mod_score += mod_adv
        sf_score  += sf_adv

        rec = {
            "move": mv,
            "position": pos,
            "mode": mode,
            "modEval": mod_ev,
            "stockfishEval": sf_ev,
            "hueco": gap,
            "huecoDetected": detected,
            "mod7": (pos["material"]*100 + pos["mobility"]*10 + pos["control"] + mv*13) % 7,
            "mod10": (pos["material"]*100 + pos["mobility"]*10 + pos["control"] + mv*13) % 10,
            "modAdvantage": mod_adv,
            "sfAdvantage": sf_adv
        }
        move_hist.append(rec)
        eval_hist.append(rec)
        prev_mode = mode
        prev_pos  = pos

    margin = {"NORMAL": 1.35, "HARD": 1.25, "VERY_HARD": 1.15}[difficulty]
    if mod_score > sf_score * margin: result = "MOD_WIN"
    elif sf_score > mod_score * margin: result = "SF_WIN"
    else: result = "DRAW"

    return {
        "moves": moves,
        "modScore": mod_score,
        "stockfishScore": sf_score,
        "result": result,
        "moveHistory": move_hist,
        "difficulty": difficulty
    }

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Simulador ANONIMUS™ vs Stockfish sintético")
    ap.add_argument("--games", type=int, default=100, help="Número de partidas (por defecto 100)")
    ap.add_argument("--difficulty", choices=["NORMAL","HARD","VERY_HARD"], default="HARD", help="Dificultad")
    ap.add_argument("--out", type=str, default="", help="Archivo JSON para guardar resultados")
    ap.add_argument("--muestra", action="store_true", help="Imprime una partida con movimientos clave")
    args = ap.parse_args()

    random.seed(42)

    results = []
    mod_w = sf_w = dr = 0
    for _ in range(args.games):
        g = simulate_game(args.difficulty)
        results.append(g)
        if g["result"] == "MOD_WIN": mod_w += 1
        elif g["result"] == "SF_WIN": sf_w += 1
        else: dr += 1

    wr = (mod_w / args.games) * 100.0
    print("\n=== ANONIMUS™ Chess Simulation ===")
    print(f"Fecha: {datetime.now().isoformat(sep=' ', timespec='seconds')}")
    print(f"Dificultad: {args.difficulty}")
    print(f"Partidas: {args.games}")
    print(f"Victorias ANONIMUS: {mod_w}")
    print(f"Victorias Stockfish: {sf_w}")
    print(f"Empates: {dr}")
    print(f"Win Rate ANONIMUS: {wr:.2f}%")

    if args.muestra and results:
        g = results[0]
        print("\n--- Partida de muestra (huecos detectados) ---")
        cnt = 0
        for m in g["moveHistory"]:
            if m["huecoDetected"]:
                cnt += 1
                if cnt > 20: break
                print(f"#{m['move']:02d} [{m['position']['phase'][:1]}] "
                      f"{m['mode']:6s}  mod7={m['mod7']}  mod10={m['mod10']}  "
                      f"Eval={m['modEval']:.1f}  SF={m['stockfishEval']:.3f}  "
                      f"Hueco=🎯 {m['hueco']:.1f}  Ventaja=+{m['modAdvantage']:.1f}")

    if args.out:
        payload = {
            "meta": {
                "date": datetime.now().isoformat(),
                "difficulty": args.difficulty,
                "games": args.games
            },
            "summary": {
                "modWins": mod_w,
                "stockfishWins": sf_w,
                "draws": dr,
                "winRate": wr
            },
            "results": results
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nGuardado en: {args.out}")

if __name__ == "__main__":
    main()
