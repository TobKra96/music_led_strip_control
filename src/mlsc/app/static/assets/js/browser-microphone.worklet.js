/** Averages the channels of each render block to mono 16-bit samples and hands them to the page. Runs in the audio thread. */
class MonoInt16Processor extends AudioWorkletProcessor {
    process(inputs) {
        const channels = inputs[0];
        if (!channels || !channels.length) return true;
        const block = new Int16Array(channels[0].length);
        for (let i = 0; i < block.length; i++) {
            let sum = 0;
            for (const channel of channels) sum += channel[i];
            const sample = Math.max(-1, Math.min(1, sum / channels.length));
            block[i] = Math.round(sample * 32767);
        }
        this.port.postMessage(block, [block.buffer]);
        return true;
    }
}

registerProcessor('mono-int16', MonoInt16Processor);
