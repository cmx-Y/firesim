//See LICENSE for license details.

package firesim.midasexamples

import chisel3._
import chisel3.util.random.LFSR
import org.chipsalliance.cde.config.Parameters

import midas.targetutils.{TriggerSource, TriggerSink, SynthesizePrintf}

object TriggerPredicatedPrintfConsts {
  val assertTriggerCycle: Int   = 100
  val deassertTriggerCycle: Int = 1000
}

/**
  * An example module that uses the trigger system to enable a printf in a
  * desired region of interest.
  *
  * Note, we're using a degenerate trigger here (we could replace it with
  * the +args for start and end cycle) it easier to verify the module works.
  *
  * @param printfPrefix Used to disambiguate printfs generated by different
  * instances of this module.
  */
class TriggerPredicatedPrintfDUT(printfPrefix: String = "SYNTHESIZED_PRINT ")
    extends Module {
  import TriggerPredicatedPrintfConsts._

  val io = IO(new Bundle{})
  // An inner class to reduce namespace bloat in midasexamples package
  class ChildModule extends Module {
    val cycle = IO(Input(UInt(16.W)))
    val lfsr = LFSR(16)

    // One means to generate a predicate. Define a wire, and drive it with the
    // TriggerSink apply method. Useful if you need something to use in expressions.
    val sinkEnable = Wire(Bool())
    TriggerSink(sinkEnable)
    when (sinkEnable) {
      SynthesizePrintf(printf(s"${printfPrefix}CYCLE: %d LFSR: %x\n", cycle, lfsr))
    }
  }

  // Rely on zero-initialization instead of reset for testing
  val cycle = Reg(UInt(16.W))
  cycle := cycle + 1.U

  val enable = cycle >= assertTriggerCycle.U && cycle <= deassertTriggerCycle.U
  TriggerSource.levelSensitiveEnable(enable)

  // DOC include start: TriggerSink.whenEnabled Usage
  /** A simpler means for predicating stateful updates, printfs, and assertions.
    *  Sugar for:
    *   val sinkEnable = Wire(Bool())
    *   TriggerSink(sinkEnable, false.B)
    *   when (sinkEnable) { <...> }
    */
  TriggerSink.whenEnabled(noSourceDefault = false.B) {
    SynthesizePrintf(printf(s"${printfPrefix}CYCLE: %d\n", cycle))
  }
  // DOC include end: TriggerSink.whenEnabled Usage

  val childInst = Module(new ChildModule)
  childInst.cycle := cycle
}


class TriggerPredicatedPrintf(implicit p: Parameters) extends firesim.lib.testutils.PeekPokeHarness(() => new TriggerPredicatedPrintfDUT)
