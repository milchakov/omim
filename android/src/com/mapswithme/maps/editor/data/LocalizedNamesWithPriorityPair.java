package com.mapswithme.maps.editor.data;

/**
 * Class which contains array of loclized names with following priority:
 *  1.Names for Mwm languages
 *  2.User`s language name
 *  3.International name
 *  4.Other names
 * and mandatoryNamesCount - count of names which should be always shown.
 */
public class LocalizedNamesWithPriorityPair {
        private LocalizedName[] mNames;
        private int mMandatoryNamesCount;

        public LocalizedNamesWithPriorityPair(LocalizedName[] names, int mandatoryNamesCount) {
            this.mNames = names;
            this.mMandatoryNamesCount = mandatoryNamesCount;
        }

        public LocalizedName[] getNames() {
            return mNames;
        }

        public int getMandatoryNamesCount() {
            return mMandatoryNamesCount;
        }
}
