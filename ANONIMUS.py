#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANONIMUS QUANTUM LENS v6.0 - MODO FINAL BOSS

Motor de ajedrez usando el sistema REAL:
- c(t) = 15M km/s variable
- Canales con fases (LANES=7)
- ω_n(t) = c(t)·k_n
- Energía local con umbrales
- Impulsos (kicks) en capturas/jaques
- Modo por energía medida NO por comparación directa
"""

import chess
import chess.engine
import numpy as np
import math
from dataclasses import dataclass

# ========== PARÁMETROS CUÁNTICOS ==========
C_BASE = 15_000_000.0  # "velocidad de la luz" variable (km/s)
LANES = 7               # canales en paralelo
EPS = 1e-9
L_DOMAIN = 1.0          # dominio espacial

@dataclass
class LenteParams:
    """Parámetros del sistema de lentes cuánticas"""
    L: float = L_DOMAIN
    c: float = C_BASE
    alpha: float = 0.10    # amplitud modulación c(t)
    beta: float = 0.05     # frecuencia modulación c(t)
    intensidad: float = 1.0
    umbral_atacar: float = 0.15   # umbral de energía para ATACAR
    umbral_pensar: float = 0.08   # umbral de energía para PENSAR

class SistemaLentesAjedrez:
    """
    Sistema de lentes cuánticas aplicado al ajedrez
    """
    def __init__(self, params: LenteParams):
        self.p = params
        self.n_canales = LANES
        # Fases de los 7 canales
        self.fases = np.linspace(0.0, 2*np.pi, self.n_canales, endpoint=False)
        self.impulso = 0.0  # acumulador de kicks
        self.hist_error = 0.0
        self.t_global = 0.0  # tiempo cuántico
    
    def c_t(self, t):
        """
        c(t) = c / (1 + α·sin(β·t))
        
        Velocidad de luz VARIABLE en el tiempo
        """
        return self.p.c / (1.0 + self.p.alpha * np.sin(self.p.beta * t))
    
    def omega_n(self, n, t):
        """
        ω_n(t) = c(t) · k_n
        donde k_n = n·π/L
        
        Frecuencia angular dependiente del tiempo
        """
        k_n = (n * np.pi) / max(self.p.L, EPS)
        return self.c_t(t) * k_n
    
    def kick(self, magnitud=0.75):
        """
        Golpe externo al sistema
        Se aplica en capturas, jaques, etc.
        """
        self.impulso += float(magnitud)
    
    def ajustar_parametros(self, error_hardware):
        """
        Ajuste dinámico de α y β basado en error medido
        """
        self.p.alpha = max(0.01, min(0.50, self.p.alpha + 0.10*error_hardware))
        self.p.beta = max(0.01, min(0.25, self.p.beta + 0.05*error_hardware))
        self.hist_error = 0.9*self.hist_error + 0.1*abs(error_hardware)
    
    def softprod(self, a, b, k=0.25):
        """Producto suave para evitar explosiones"""
        return np.sign(a*b) * (np.abs(a*b)**(1.0/(1.0+k)))
    
    def calcular_canal(self, x, t, n, fase_canal, indice_i, deltaC, S):
        """
        Calcula un canal cuántico individual
        
        Ψ_canal = sin(k_n·x) · e^(-iω_n(t)·t) + caos
        
        Devuelve energía y modo
        """
        k_n = (n * np.pi) / max(self.p.L, EPS)
        omega = self.omega_n(n, t)
        
        # Señal base compleja
        base = np.sin(k_n * x) * np.exp(-1j * omega * t)
        
        # Componente caótica
        caos = 0.35*np.sin(0.7*t + fase_canal) + 0.65*np.cos(0.41*t + 0.5*fase_canal)
        
        # Error de hardware simulado
        err_hw = 0.12*np.sin(0.13*t + fase_canal) + 0.05*np.random.uniform(-1, 1)
        self.ajustar_parametros(err_hw)
        
        # Mezcla análisis (suma) vs forzar (producto)
        analizar = np.real(base) + caos
        forzar = self.softprod(np.real(base), (S**deltaC) * (1.0 + 0.10*indice_i))
        
        # Calcular ENERGÍA LOCAL
        energia_analizar = np.mean(analizar**2)
        energia_forzar = np.mean(forzar**2)
        
        # Decisión por UMBRAL de energía
        energia_total = energia_analizar + energia_forzar + self.impulso
        
        if energia_total > self.p.umbral_atacar:
            modo = "ATACAR"
            salida = forzar * (1.0 + 0.25*self.impulso) * self.p.intensidad
        elif energia_total > self.p.umbral_pensar:
            modo = "PENSAR"
            salida = analizar * self.p.intensidad
        else:
            modo = "LATENTE"
            salida = (analizar + forzar) * 0.5 * self.p.intensidad
        
        return salida, modo, energia_total
    
    def funcion_onda_movimiento(self, board, move, move_number):
        """
        Evalúa un movimiento usando superposición de canales cuánticos
        
        Cada movimiento genera su propio campo cuántico
        """
        # Mapear características del tablero a parámetros cuánticos
        material = self.calcular_material(board)
        mobility = len(list(board.legal_moves))
        
        # Coordenadas cuánticas del movimiento
        x = np.array([0.1, 0.3, 0.5, 0.7, 0.9])  # puntos de muestreo
        
        # Índices de canalización
        indice_i = (material % 10) + 1
        deltaC = 0.5 + (mobility / 100.0)
        S = 1.0 + (move_number / 100.0)
        
        # Tiempo cuántico
        t = self.t_global
        
        # Superposición de canales
        field_total = np.zeros_like(x, dtype=float)
        energias = []
        modos_canales = []
        
        for k in range(self.n_canales):
            fase_k = self.fases[k]
            canal_sum = np.zeros_like(x, dtype=float)
            
            # Combinar armónicos n=1,2,3
            for n in [1, 2, 3]:
                salida, modo, energia = self.calcular_canal(
                    x, t, n, fase_k, indice_i, deltaC, S
                )
                canal_sum += salida
                energias.append(energia)
                modos_canales.append(modo)
            
            field_total += canal_sum
        
        # Normalizar campo
        field_total *= 1.0 / max(1.0, np.max(np.abs(field_total)) + 1e-6)
        
        # Energía total medida
        energia_total = np.mean([e for e in energias])
        
        # Modo dominante por votación de canales
        modo_atacar = sum(1 for m in modos_canales if m == "ATACAR")
        modo_pensar = sum(1 for m in modos_canales if m == "PENSAR")
        
        if modo_atacar > modo_pensar:
            modo_final = "ATACAR"
        else:
            modo_final = "PENSAR"
        
        # Score basado en energía y modo
        score = energia_total * 100.0
        if modo_final == "ATACAR":
            score *= 1.5
        
        # Decaer impulso
        self.impulso *= 0.96
        
        return {
            'score': score,
            'energia': energia_total,
            'modo': modo_final,
            'canales_atacar': modo_atacar,
            'canales_pensar': modo_pensar,
            'c_t': self.c_t(t),
            'impulso': self.impulso
        }
    
    def calcular_material(self, board):
        """Balance material simple"""
        values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                  chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
        white = sum(len(board.pieces(pt, chess.WHITE)) * val for pt, val in values.items())
        black = sum(len(board.pieces(pt, chess.BLACK)) * val for pt, val in values.items())
        return abs(white - black)
    
    def avanzar_tiempo(self, dt=0.1):
        """Avanza el tiempo cuántico del sistema"""
        self.t_global += dt

# ========== MOTOR DE AJEDREZ ==========

def evaluar_movimiento_lentes(board, move, move_number, sistema_lentes):
    """
    Evalúa movimiento con sistema de lentes cuánticas
    """
    board.push(move)
    
    evaluacion = sistema_lentes.funcion_onda_movimiento(board, move, move_number)
    
    # Aplicar kicks por eventos especiales
    if board.is_check():
        sistema_lentes.kick(0.8)
        evaluacion['score'] += 50
    
    if board.is_capture(move):
        sistema_lentes.kick(0.5)
        evaluacion['score'] += 30
    
    board.pop()
    
    return evaluacion

def seleccionar_movimiento_lentes(board, move_number, sistema_lentes):
    """
    Selecciona mejor movimiento usando lentes cuánticas
    """
    legal_moves = list(board.legal_moves)
    
    if not legal_moves:
        return None, None
    
    mejor_move = None
    mejor_eval = None
    mejor_score = float('-inf')
    
    for move in legal_moves:
        evaluacion = evaluar_movimiento_lentes(board, move, move_number, sistema_lentes)
        
        if evaluacion['score'] > mejor_score:
            mejor_score = evaluacion['score']
            mejor_move = move
            mejor_eval = evaluacion
    
    # Avanzar tiempo cuántico
    sistema_lentes.avanzar_tiempo(0.08)
    
    return mejor_move, mejor_eval

# ========== JUGAR PARTIDA ==========

def jugar_modo_final_boss(stockfish_depth=8, verbose=True):
    """
    Partida con sistema de lentes cuánticas COMPLETO
    """
    board = chess.Board()
    
    try:
        engine = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")
        engine.configure({"Skill Level": 20})
    except Exception as e:
        print(f"Error: {e}")
        return None
    
    # Inicializar sistema de lentes
    params = LenteParams()
    sistema = SistemaLentesAjedrez(params)
    
    move_number = 0
    
    print("\n" + "="*70)
    print("🌀 ANONIMUS QUANTUM LENS - MODO FINAL BOSS")
    print("="*70)
    print(f"c(t) base = {C_BASE:,.0f} km/s (variable)")
    print(f"Canales cuánticos: {LANES}")
    print(f"Umbral ATACAR: {params.umbral_atacar}")
    print(f"Umbral PENSAR: {params.umbral_pensar}")
    print("="*70)
    
    while not board.is_game_over() and move_number < 100:
        move_number += 1
        
        if board.turn == chess.WHITE:  # ANONIMUS
            move, evaluacion = seleccionar_movimiento_lentes(board, move_number, sistema)
            
            if move and evaluacion:
                if verbose and move_number % 10 == 0:
                    print(f"\n🌀 Move #{move_number} - {board.san(move)}")
                    print(f"   Modo: {evaluacion['modo']}")
                    print(f"   Energía: {evaluacion['energia']:.4f}")
                    print(f"   c(t): {evaluacion['c_t']:,.0f} km/s")
                    print(f"   Canales: ATACAR={evaluacion['canales_atacar']}, PENSAR={evaluacion['canales_pensar']}")
                    print(f"   Impulso acumulado: {evaluacion['impulso']:.3f}")
                    print(f"   α={sistema.p.alpha:.3f}, β={sistema.p.beta:.3f}")
        else:
            result = engine.play(board, chess.engine.Limit(depth=stockfish_depth))
            move = result.move
        
        if move:
            board.push(move)
    
    engine.quit()
    
    result = board.result()
    winner = "ANONIMUS" if result == "1-0" else "STOCKFISH" if result == "0-1" else "EMPATE"
    
    print("\n" + "="*70)
    print(f"Resultado: {result} - {winner}")
    print(f"Tiempo cuántico final: t={sistema.t_global:.2f}")
    print(f"Parámetros finales: α={sistema.p.alpha:.3f}, β={sistema.p.beta:.3f}")
    print(f"Error acumulado: {sistema.hist_error:.4f}")
    print("="*70 + "\n")
    
    return {
        'resultado': result,
        'ganador': winner,
        'movimientos': move_number,
        'tiempo_cuantico': sistema.t_global,
        'alpha_final': sistema.p.alpha,
        'beta_final': sistema.p.beta
    }

# ========== MAIN ==========

def main():
    print("\n" + "="*70)
    print("🌀 ANONIMUS QUANTUM LENS v6.0")
    print("="*70)
    print("Sistema REAL con:")
    print("  • c(t) = 15M km/s variable")
    print("  • 7 canales cuánticos con fases")
    print("  • ω_n(t) = c(t)·k_n")
    print("  • Energía local con umbrales")
    print("  • Impulsos en capturas/jaques")
    print("  • Modo por medición de energía")
    print("="*70 + "\n")
    
    num_games = int(input("¿Cuántas partidas para el MODO FINAL BOSS? (1-5): ") or "3")
    
    resultados = {"ANONIMUS": 0, "STOCKFISH": 0, "EMPATE": 0}
    
    for i in range(num_games):
        print(f"\n{'='*70}")
        print(f"PARTIDA {i+1}/{num_games} - FINAL BOSS MODE")
        print(f"{'='*70}")
        
        partida = jugar_modo_final_boss(
            stockfish_depth=8,
            verbose=(i==0)
        )
        
        if partida:
            resultados[partida['ganador']] += 1
    
    print("\n" + "="*70)
    print("📊 RESULTADOS MODO FINAL BOSS")
    print("="*70)
    print(f"🏆 Victorias ANONIMUS:  {resultados['ANONIMUS']}")
    print(f"🤖 Victorias Stockfish: {resultados['STOCKFISH']}")
    print(f"🤝 Empates:             {resultados['EMPATE']}")
    
    if num_games > 0:
        wr = (resultados['ANONIMUS'] / num_games) * 100
        print(f"\n📈 Win Rate: {wr:.1f}%")
        
        if resultados['ANONIMUS'] > 0:
            print("\n🎉 ¡IMPRESIONANTE! El sistema cuántico logró victoria(s)")
        elif resultados['EMPATE'] > 0:
            print("\n💪 Sistema cuántico aguantó empate(s)")
        else:
            print("\n🤔 Sistema cuántico necesita más calibración")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
